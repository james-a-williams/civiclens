import logging
import os
from typing import Any

from .base import BaseConnector, ConnectorError

logger = logging.getLogger(__name__)

CURRENT_CYCLE = 2024


class FECConnector(BaseConnector):
    """Federal Election Commission campaign finance data.

    Covers candidates, committees, individual contributions (Schedule A),
    and disbursements (Schedule B) for federal races.
    Docs: https://api.open.fec.gov/developers
    """

    SOURCE_NAME = "fec"
    BASE_URL = "https://api.open.fec.gov/v1"

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__()
        key = api_key or os.environ["FEC_API_KEY"]
        # session.params merges with every request's params automatically
        self._session.params = {"api_key": key}  # type: ignore[assignment]

    def get_candidates(self, cycle: int = CURRENT_CYCLE, office: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"election_year": cycle, "sort": "name"}
        if office:
            params["office"] = office
        return list(self._paginate("/candidates/search", params, "results"))

    def get_candidate(self, candidate_id: str) -> dict:
        data = self._get(f"/candidate/{candidate_id}")
        results = data.get("results", [])
        if not results:
            raise ConnectorError(f"candidate {candidate_id!r} not found")
        return results[0]

    def get_committees(self, cycle: int = CURRENT_CYCLE) -> list[dict]:
        params: dict[str, Any] = {"cycle": cycle, "sort": "name"}
        return list(self._paginate("/committees", params, "results"))

    def get_committee(self, committee_id: str) -> dict:
        data = self._get(f"/committee/{committee_id}")
        results = data.get("results", [])
        if not results:
            raise ConnectorError(f"committee {committee_id!r} not found")
        return results[0]

    def get_candidate_totals(self, cycle: int = CURRENT_CYCLE) -> list[dict]:
        """Financial totals (receipts, disbursements, cash on hand) for all candidates."""
        params: dict[str, Any] = {"cycle": cycle, "sort": "candidate_id"}
        return list(self._paginate("/candidates/totals", params, "results"))

    def get_contributions(self, candidate_id: str, cycle: int = CURRENT_CYCLE) -> list[dict]:
        """Individual contributions received (Schedule A) for a candidate."""
        params: dict[str, Any] = {
            "candidate_id": candidate_id,
            "two_year_transaction_period": cycle,
            "sort": "-contribution_receipt_date",
        }
        return list(self._paginate("/schedules/schedule_a", params, "results"))

    def get_disbursements(self, committee_id: str, cycle: int = CURRENT_CYCLE) -> list[dict]:
        """Disbursements made (Schedule B) by a committee."""
        params: dict[str, Any] = {
            "committee_id": committee_id,
            "two_year_transaction_period": cycle,
            "sort": "-disbursement_date",
        }
        return list(self._paginate("/schedules/schedule_b", params, "results"))

    def fetch_all(self, cycle: int = CURRENT_CYCLE) -> dict[str, list[dict]]:  # type: ignore[override]
        logger.info("FEC: fetching candidates cycle=%d", cycle)
        candidates = self.get_candidates(cycle=cycle)

        logger.info("FEC: fetching committees cycle=%d", cycle)
        committees = self.get_committees(cycle=cycle)

        logger.info("FEC: fetching candidate totals cycle=%d", cycle)
        candidate_totals = self.get_candidate_totals(cycle=cycle)

        return {
            "candidates": candidates,
            "committees": committees,
            "candidate_totals": candidate_totals,
        }
