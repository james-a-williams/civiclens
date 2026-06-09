import logging
import os
from typing import Any, Iterator

from .base import BaseConnector, ConnectorError

logger = logging.getLogger(__name__)

CURRENT_CONGRESS = 119  # 119th Congress: Jan 2025 – Jan 2027


class CongressAPIConnector(BaseConnector):
    """Congress.gov API — members, bills, votes, and committees.

    Canonical source for federal legislative activity. Uses bioguideId as
    the stable primary key for members across all congresses.
    Docs: https://github.com/LibraryOfCongress/api.congress.gov
    """

    SOURCE_NAME = "congress"
    BASE_URL = "https://api.congress.gov/v3"

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__()
        key = api_key or os.environ["CONGRESS_API_KEY"]
        self._session.params = {"api_key": key, "format": "json"}  # type: ignore[assignment]

    def _paginate_congress(
        self, path: str, params: dict[str, Any], results_key: str
    ) -> Iterator[dict]:
        """Yield records using Congress.gov offset/limit pagination."""
        params = {**params, "offset": 0, "limit": 250}
        while True:
            data = self._get(path, params)
            records = data.get(results_key, [])
            if not records:
                break
            yield from records
            if not data.get("pagination", {}).get("next"):
                break
            params["offset"] += len(records)

    def get_members(
        self, congress: int = CURRENT_CONGRESS, chamber: str | None = None
    ) -> list[dict]:
        params: dict[str, Any] = {"congress": congress}
        if chamber:
            params["chamber"] = chamber
        return list(self._paginate_congress("/member", params, "members"))

    def get_member(self, bioguide_id: str) -> dict:
        data = self._get(f"/member/{bioguide_id}")
        member = data.get("member")
        if not member:
            raise ConnectorError(f"member {bioguide_id!r} not found")
        return member

    def get_sponsored_legislation(self, bioguide_id: str) -> list[dict]:
        return list(
            self._paginate_congress(
                f"/member/{bioguide_id}/sponsored-legislation",
                {},
                "sponsoredLegislation",
            )
        )

    def get_bills(
        self, congress: int = CURRENT_CONGRESS, bill_type: str = "hr"
    ) -> list[dict]:
        return list(self._paginate_congress(f"/bill/{congress}/{bill_type}", {}, "bills"))

    def get_bill_votes(
        self, congress: int, bill_type: str, bill_number: int
    ) -> list[dict]:
        data = self._get(f"/bill/{congress}/{bill_type}/{bill_number}/votes")
        return data.get("votes", [])

    def get_committees(self, chamber: str = "house") -> list[dict]:
        return list(self._paginate_congress(f"/committee/{chamber}", {}, "committees"))

    def fetch_all(self, congress: int = CURRENT_CONGRESS) -> dict[str, list[dict]]:  # type: ignore[override]
        logger.info("Congress API: fetching members congress=%d", congress)
        members = self.get_members(congress=congress)

        logger.info("Congress API: fetching committees")
        house_committees = self.get_committees(chamber="house")
        senate_committees = self.get_committees(chamber="senate")

        return {
            "members": members,
            "house_committees": house_committees,
            "senate_committees": senate_committees,
        }
