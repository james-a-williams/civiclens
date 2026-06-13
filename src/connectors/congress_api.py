import logging
import os
import xml.etree.ElementTree as ET
from typing import Any, Iterator

from .base import BaseConnector, ConnectorError

logger = logging.getLogger(__name__)

CURRENT_CONGRESS = 119  # 119th Congress: Jan 2025 – Jan 2027
CURRENT_SESSION = 1
CURRENT_YEAR = 2025

BILL_TYPES = ["hr", "s", "hjres", "sjres", "hres", "sres"]

_VOTE_OPTION_MAP = {
    "yea": "yes",
    "aye": "yes",
    "nay": "no",
    "no": "no",
    "not voting": "abstain",
    "present": "present",
}


class CongressAPIConnector(BaseConnector):
    """Congress.gov API — members, bills, votes, and committees.

    Canonical source for federal legislative activity. Uses bioguideId as
    the stable primary key for members across all congresses.
    Docs: https://github.com/LibraryOfCongress/api.congress.gov

    Roll-call votes are fetched from:
    - House: House Clerk XML (clerk.house.gov/evs/{year}/roll{N:03d}.xml)
    - Senate: Senate LIS XML (senate.gov/legislative/LIS/roll_call_votes/...)
    Neither endpoint requires authentication.
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

    def get_all_bills(self, congress: int = CURRENT_CONGRESS) -> list[dict]:
        """Fetch bills across all bill types for a given Congress."""
        all_bills: list[dict] = []
        for bill_type in BILL_TYPES:
            logger.info("Congress API: fetching %s bills congress=%d", bill_type, congress)
            bills = self.get_bills(congress, bill_type)
            all_bills.extend(bills)
        return all_bills

    def get_all_member_sponsorships(self, members: list[dict]) -> list[dict]:
        """Fetch sponsored legislation for every member, tagging each row with bioguide_id."""
        all_sponsorships: list[dict] = []
        for member in members:
            bioguide_id = member.get("bioguideId")
            if not bioguide_id:
                continue
            try:
                legislation = self.get_sponsored_legislation(bioguide_id)
                for leg in legislation:
                    leg["_bioguide_id"] = bioguide_id
                all_sponsorships.extend(legislation)
            except Exception as exc:
                logger.warning(
                    "Congress API: failed to get sponsorships for %s: %s", bioguide_id, exc
                )
        return all_sponsorships

    def _parse_house_vote_xml(self, content: bytes, roll_number: int, year: int) -> dict:
        root = ET.fromstring(content)
        meta = root.find("vote-metadata")

        def mtext(tag: str) -> str | None:
            el = meta.find(tag) if meta is not None else None
            return el.text.strip() if el is not None and el.text else None

        member_votes = []
        for rv in root.findall(".//recorded-vote"):
            leg = rv.find("legislator")
            option_raw = (rv.findtext("vote") or "").lower()
            if leg is not None:
                member_votes.append({
                    "bioguide_id": leg.get("name-id"),
                    "name": leg.text,
                    "party": leg.get("party"),
                    "state": leg.get("state"),
                    "option": _VOTE_OPTION_MAP.get(option_raw, option_raw),
                })

        return {
            "chamber": "house",
            "congress": mtext("congress"),
            "session": mtext("session"),
            "roll_number": roll_number,
            "year": year,
            "legis_num": mtext("legis-num"),
            "vote_question": mtext("vote-question"),
            "vote_result": mtext("vote-result"),
            "action_date": mtext("action-date"),
            "member_votes": member_votes,
        }

    def get_house_votes(self, year: int = CURRENT_YEAR, max_rolls: int = 2000) -> list[dict]:
        """Fetch all House roll-call votes for a year from House Clerk XML.

        Iterates roll numbers sequentially until a 404 indicates no more rolls.
        Does not use the Congress.gov API key — House Clerk is unauthenticated.
        """
        results: list[dict] = []
        for roll in range(1, max_rolls + 1):
            url = f"https://clerk.house.gov/evs/{year}/roll{roll:03d}.xml"
            resp = self._session.get(url, timeout=30)
            if resp.status_code == 404:
                logger.info(
                    "Congress API: House votes — %d rolls fetched for year=%d", roll - 1, year
                )
                break
            if resp.status_code >= 400:
                logger.warning(
                    "Congress API: House vote roll=%d year=%d returned %d, skipping",
                    roll, year, resp.status_code,
                )
                continue
            results.append(self._parse_house_vote_xml(resp.content, roll, year))
        return results

    def _parse_senate_vote_xml(self, content: bytes) -> dict:
        root = ET.fromstring(content)

        def rtext(tag: str) -> str | None:
            el = root.find(tag)
            return el.text.strip() if el is not None and el.text else None

        doc = root.find("document")
        legis_num = None
        if doc is not None:
            doc_type = doc.findtext("document_type", "").strip()
            doc_num = doc.findtext("document_number", "").strip()
            if doc_type and doc_num:
                legis_num = f"{doc_type} {doc_num}"

        member_votes = []
        for member in root.findall(".//member"):
            option_raw = (member.findtext("vote_cast") or "").lower()
            member_votes.append({
                "lis_member_id": member.findtext("lis_member_id"),
                "name": member.findtext("member_full"),
                "party": member.findtext("party"),
                "state": member.findtext("state"),
                "option": _VOTE_OPTION_MAP.get(option_raw, option_raw),
            })

        return {
            "chamber": "senate",
            "congress": rtext("congress"),
            "session": rtext("session"),
            "vote_number": rtext("vote_number"),
            "vote_date": rtext("vote_date"),
            "legis_num": legis_num,
            "vote_question": rtext("question"),
            "vote_result": rtext("vote_result"),
            "member_votes": member_votes,
        }

    def get_senate_votes(
        self,
        congress: int = CURRENT_CONGRESS,
        session: int = CURRENT_SESSION,
        max_votes: int = 2000,
    ) -> list[dict]:
        """Fetch all Senate roll-call votes for a Congress session from Senate LIS XML.

        Iterates vote numbers sequentially until a 404 indicates no more votes.
        Does not use the Congress.gov API key — Senate LIS is unauthenticated.
        """
        results: list[dict] = []
        for vote_num in range(1, max_votes + 1):
            url = (
                f"https://www.senate.gov/legislative/LIS/roll_call_votes"
                f"/vote{congress}{session}"
                f"/vote_{congress}_{session}_{vote_num:05d}.xml"
            )
            resp = self._session.get(url, timeout=30)
            if resp.status_code == 404:
                logger.info(
                    "Congress API: Senate votes — %d votes fetched for congress=%d session=%d",
                    vote_num - 1, congress, session,
                )
                break
            if resp.status_code >= 400:
                logger.warning(
                    "Congress API: Senate vote=%d congress=%d session=%d returned %d, skipping",
                    vote_num, congress, session, resp.status_code,
                )
                continue
            results.append(self._parse_senate_vote_xml(resp.content))
        return results

    def fetch_all(self, congress: int = CURRENT_CONGRESS) -> dict[str, list[dict]]:  # type: ignore[override]
        logger.info("Congress API: fetching members congress=%d", congress)
        members = self.get_members(congress=congress)

        logger.info("Congress API: fetching committees")
        house_committees = self.get_committees(chamber="house")
        senate_committees = self.get_committees(chamber="senate")

        logger.info("Congress API: fetching bills congress=%d", congress)
        bills = self.get_all_bills(congress)

        logger.info("Congress API: fetching sponsored legislation for %d members", len(members))
        member_sponsorships = self.get_all_member_sponsorships(members)

        logger.info("Congress API: fetching House roll-call votes year=%d", CURRENT_YEAR)
        house_votes = self.get_house_votes(year=CURRENT_YEAR)

        logger.info(
            "Congress API: fetching Senate roll-call votes congress=%d session=%d",
            congress, CURRENT_SESSION,
        )
        senate_votes = self.get_senate_votes(congress=congress, session=CURRENT_SESSION)

        return {
            "members": members,
            "house_committees": house_committees,
            "senate_committees": senate_committees,
            "congress_bills": bills,
            "congress_member_sponsorships": member_sponsorships,
            "congress_house_votes": house_votes,
            "congress_senate_votes": senate_votes,
        }
