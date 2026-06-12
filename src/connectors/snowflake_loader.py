import argparse
import logging
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv
from snowflake.connector.pandas_tools import write_pandas

from .census import CensusConnector
from .congress_api import CongressAPIConnector
from .fec import FECConnector
from .ny_boe import NYBOEConnector
from .nyc_cfb import NYCCFBConnector
from .openstates import OpenStatesConnector
from .snowflake_client import get_raw_connection

logger = logging.getLogger(__name__)


def load_table(conn, records: list[dict], table_name: str) -> None:
    if not records:
        logger.warning("load_table: no records for %s, skipping", table_name)
        return
    df = pd.DataFrame(records)
    df["load_at"] = datetime.now(timezone.utc)
    df.columns = df.columns.str.upper().str.replace(" ", "_")
    df = df.loc[:, df.columns.notna()]  # drop phantom columns from trailing CSV commas
    write_pandas(conn, df, table_name.upper(), auto_create_table=True, overwrite=True, use_logical_type=True)
    logger.info("load_table: wrote %d rows → %s", len(df), table_name)


def load_connector_data(conn, tables: dict[str, list[dict]]) -> None:
    for table_name, records in tables.items():
        load_table(conn, records, table_name)


CONNECTORS = [
    (CongressAPIConnector, "CONGRESS_API_KEY"),
    (FECConnector, "FEC_API_KEY"),
    (OpenStatesConnector, "OPENSTATES_API_KEY"),
    (CensusConnector, "CENSUS_API_KEY"),
    (NYBOEConnector, ""),
    (NYCCFBConnector, ""),
]


def load_all() -> None:
    parser = argparse.ArgumentParser(description="Load CivicLens raw data into Snowflake")
    parser.add_argument(
        "--source",
        metavar="NAME",
        help="Run only this source (e.g. census, fec). Omit to run all.",
    )
    args = parser.parse_args()

    load_dotenv()
    conn = get_raw_connection()
    try:
        for connector_cls, _ in CONNECTORS:
            name = connector_cls.SOURCE_NAME
            if args.source and name != args.source:
                continue
            logger.info("load_all: starting %s", name)
            connector = connector_cls()
            tables = connector.fetch_all()
            counts = {t: len(r) for t, r in tables.items()}
            logger.info("load_all: %s tables=%s", name, counts)
            load_connector_data(conn, tables)
            logger.info("load_all: finished %s", name)
    finally:
        conn.close()
