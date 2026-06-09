import logging
import os
from typing import Any, Iterator

from .base import BaseConnector, ConnectorError

logger = logging.getLogger(__name__)


class OpenStatesConnector(BaseConnector):
    """OpenStates API v3 — state legislators, bills, and votes for all 50 states.

    Free tier: ~500 requests/day. Jurisdiction IDs use OCD format:
    e.g. `ocd-jurisdiction/country:us/state:ca/government`
    Docs: https://docs.openstates.org/api-v3/
    """

    SOURCE_NAME = "openstates"
    BASE_URL = "https://v3.openstates.org"

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__()
        key = api_key or os.environ["OPENSTATES_API_KEY"]
        self._session.headers.update({"X-API-Key": key})

    def _paginate_openstates(
        self, path: str, params: dict[str, Any], per_page: int = 20
    ) -> Iterator[dict]:
        """Yield records using OpenStates page/max_page pagination."""
        params = {**params, "page": 1, "per_page": per_page}
        while True:
            data = self._get(path, params)
            records = data.get("results", [])
            if not records:
                break
            yield from records
            pagination = data.get("pagination", {})
            if params["page"] >= pagination.get("max_page", 1):
                break
            params["page"] += 1

    def get_jurisdictions(self) -> list[dict]:
        data = self._get("/jurisdictions", {"classification": "government"})
        return data.get("results", [])

    def get_people(self, state: str) -> list[dict]:
        """Fetch current legislators for a state. Uses short state code (e.g. 'ca')."""
        params: dict[str, Any] = {"jurisdiction": state.lower()}
        return list(self._paginate_openstates("/people", params))

    def get_person(self, openstates_id: str) -> dict:
        data = self._get(f"/people/{openstates_id}")
        if not data:
            raise ConnectorError(f"person {openstates_id!r} not found")
        return data

    def get_bills(
        self,
        state: str,
        session: str | None = None,
        subject: str | None = None,
    ) -> list[dict]:
        params: dict[str, Any] = {"jurisdiction": state.lower()}
        if session:
            params["session"] = session
        if subject:
            params["subject"] = subject
        return list(self._paginate_openstates("/bills", params))

    def get_bill_votes(self, bill_id: str) -> list[dict]:
        data = self._get(f"/bills/{bill_id}/votes")
        return data.get("results", [])

    def fetch_all(self, states: list[str] | None = None) -> dict[str, list[dict]]:  # type: ignore[override]
        target_states = states or ["ca", "tx", "ny", "fl", "il"]
        all_people: list[dict] = []
        all_bills: list[dict] = []

        for state in target_states:
            logger.info("OpenStates: fetching people state=%s", state)
            people = self.get_people(state)
            for p in people:
                p["_state"] = state
            all_people.extend(people)

            logger.info("OpenStates: fetching bills state=%s", state)
            bills = self.get_bills(state)
            for b in bills:
                b["_state"] = state
            all_bills.extend(bills)

        return {"people": all_people, "bills": all_bills}
