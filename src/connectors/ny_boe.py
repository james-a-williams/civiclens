import csv
import logging
from pathlib import Path
from typing import Any

from .base import BaseConnector, ConnectorError

logger = logging.getLogger(__name__)


class NYBOEConnector(BaseConnector):
    """NY State Board of Elections public campaign finance activity.

    Reads manually downloaded CSV files from `data/raw/ny_boe/`. Each file covers
    one election year and contains one row per candidate showing public funds received
    and qualified campaign expenditures.

    To refresh data: download updated files from
    https://publicreporting.elections.ny.gov/DownloadCampaignFinanceData/
    and place them in data/raw/ny_boe/.

    Confirmed CSV columns:
        Election Year, Filer ID, Committee Name, Candidate Name, Office,
        District, Public Funds Received, Qualified Campaign Expenditures
    """

    SOURCE_NAME = "ny_boe"
    BASE_URL = ""
    DEFAULT_DATA_DIR = Path("data/raw/ny_boe")

    def get_activity(self, data_dir: Path | None = None) -> list[dict[str, Any]]:
        directory = data_dir or self.DEFAULT_DATA_DIR
        if not directory.exists():
            raise ConnectorError(
                f"NYSBOE data directory not found: {directory}. "
                "Download CSV files from publicreporting.elections.ny.gov and place "
                "them in that directory."
            )

        csv_files = sorted(directory.glob("*.csv"))
        if not csv_files:
            raise ConnectorError(
                f"No CSV files found in {directory}. "
                "Download CSV files from publicreporting.elections.ny.gov."
            )

        all_records: list[dict[str, Any]] = []
        for path in csv_files:
            logger.info("NYSBOE: reading %s", path.name)
            with path.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                records = list(reader)
            all_records.extend(records)
            logger.info("NYSBOE: %s loaded %d records", path.name, len(records))

        return all_records

    def fetch_all(self, data_dir: Path | None = None) -> dict[str, list[dict]]:  # type: ignore[override]
        activity = self.get_activity(data_dir=data_dir)
        return {"ny_boe_activity": activity}
