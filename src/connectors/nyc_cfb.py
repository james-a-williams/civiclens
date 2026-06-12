import csv
import io
import logging
from typing import Any

from .base import BaseConnector

logger = logging.getLogger(__name__)

# Election cycles available for download. The last ~10 years covers 2017–2025.
# Schema documented in https://www.nyccfb.info/DataLibrary/Key-Contribution.csv
DEFAULT_CYCLES = [2017, 2021, 2023, 2025]

# Direct CSV download paths per cycle.
# The 2025 path uses a different casing than older cycles (server-side quirk).
_CYCLE_PATHS: dict[int, str] = {
    2017: "/DataLibrary/2017_Contributions.csv",
    2021: "/DataLibrary/2021_Contributions.csv",
    2023: "/DataLibrary/2023_Contributions.csv",
    2025: "/datalibrary/2025_Contributions.csv",
}


class NYCCFBConnector(BaseConnector):
    """NYC Campaign Finance Board contribution records.

    Covers contributions to NYC city races (mayor, city council, public advocate,
    borough president, comptroller). No API key required.
    Data library: https://www.nyccfb.info/follow-the-money/data-library/
    """

    SOURCE_NAME = "nyc_cfb"
    BASE_URL = "https://www.nyccfb.info"

    def get_contributions(self, cycles: list[int] | None = None) -> list[dict[str, Any]]:
        target_cycles = cycles or DEFAULT_CYCLES
        all_contributions: list[dict[str, Any]] = []

        for cycle in target_cycles:
            path = _CYCLE_PATHS.get(cycle)
            if not path:
                logger.warning("NYC CFB: no download path for cycle %d, skipping", cycle)
                continue

            logger.info("NYC CFB: fetching cycle=%d", cycle)
            resp = self._session.get(self.BASE_URL + path, timeout=180)
            resp.raise_for_status()

            reader = csv.DictReader(io.StringIO(resp.text))
            records: list[dict[str, Any]] = []
            for row in reader:
                row["cycle_year"] = cycle
                records.append(dict(row))

            all_contributions.extend(records)
            logger.info("NYC CFB: cycle=%d loaded %d records", cycle, len(records))

        return all_contributions

    def fetch_all(self, cycles: list[int] | None = None) -> dict[str, list[dict]]:  # type: ignore[override]
        contributions = self.get_contributions(cycles=cycles)
        return {"nyc_cfb_contributions": contributions}
