"""Historical data backfill — Congress 111–119 and FEC cycles 2010–2024.

Run once after the warehouse is set up to populate history. Safe to re-run:
staging models deduplicate on (primary_key, load_at desc), so re-ingesting a
congress or cycle just adds ignorable duplicates that staging filters out.

Usage:
    civiclens-backfill                        # all sources, full history
    civiclens-backfill --source congress      # Congress only
    civiclens-backfill --source fec           # FEC only
    civiclens-backfill --congress 118         # single Congress (useful for reruns)
    civiclens-backfill --cycle 2020           # single FEC cycle
"""

import argparse
import logging
import time

from dotenv import load_dotenv

from ..connectors.congress_api import CONGRESS_RANGE, CongressAPIConnector
from ..connectors.fec import FEC_CYCLES, FECConnector
from ..connectors.snowflake_client import get_raw_connection
from ..connectors.snowflake_loader import load_connector_data

logger = logging.getLogger(__name__)


def backfill_congress(conn, congresses: list[int]) -> None:
    connector = CongressAPIConnector()
    for congress in congresses:
        t0 = time.time()
        logger.info("backfill congress: %dth Congress — start", congress)
        tables = connector.fetch_all(congress=congress)
        counts = {t: len(r) for t, r in tables.items()}
        logger.info("backfill congress: %d fetched %s", congress, counts)
        load_connector_data(conn, tables, overwrite=False)
        logger.info("backfill congress: %d done in %.1fs", congress, time.time() - t0)


def backfill_fec(conn, cycles: list[int]) -> None:
    connector = FECConnector()
    for cycle in cycles:
        t0 = time.time()
        logger.info("backfill fec: cycle %d — start", cycle)
        tables = connector.fetch_all(cycle=cycle)
        counts = {t: len(r) for t, r in tables.items()}
        logger.info("backfill fec: cycle %d fetched %s", cycle, counts)
        load_connector_data(conn, tables, overwrite=False)
        logger.info("backfill fec: cycle %d done in %.1fs", cycle, time.time() - t0)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CivicLens historical data backfill (Congress 111–119, FEC 2010–2024)"
    )
    parser.add_argument(
        "--source", choices=["congress", "fec"],
        help="Run only this source. Omit to run both.",
    )
    parser.add_argument(
        "--congress", type=int, metavar="N",
        help="Load a single Congress number instead of the full range.",
    )
    parser.add_argument(
        "--cycle", type=int, metavar="YEAR",
        help="Load a single FEC cycle year instead of the full range.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    load_dotenv()
    conn = get_raw_connection()

    try:
        if args.source in (None, "congress"):
            congresses = [args.congress] if args.congress else CONGRESS_RANGE
            backfill_congress(conn, congresses)

        if args.source in (None, "fec"):
            cycles = [args.cycle] if args.cycle else FEC_CYCLES
            backfill_fec(conn, cycles)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
