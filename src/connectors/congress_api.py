import logging
import os
import xml.etree.ElementTree as ET
from typing import Any, Iterator

import yaml

from .base import BaseConnector, ConnectorError

logger = logging.getLogger(__name__)

CURRENT_CONGRESS = 119  # 119th Congress: Jan 2025 – Jan 2027
CURRENT_SESSION = 1
CURRENT_YEAR = 2025

# Historical range: 111th (Jan 2009) through current
CONGRESS_RANGE = list(range(111, CURRENT_CONGRESS + 1))

BILL_TYPES = ["hr", "s", "hjres", "sjres", "hres", "sres"]


def congress_years(congress: int) -> tuple[int, int]:
    """Return the two calendar years covered by a Congress (e.g. 119 → (2025, 2026))."""
    start = 2009 + 2 * (congress - 111)
    return start, start + 1

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

    _LEGISLATORS_BASE = (
        "https://raw.githubusercontent.com/unitedstates/congress-legislators/refs/heads/main"
    )

    def get_committee_memberships(self, congress: int = CURRENT_CONGRESS) -> list[dict]:
        """Fetch committee memberships from the unitedstates/congress-legislators dataset.

        Congress.gov API does not expose committee member lists; this uses the
        community-maintained legislators dataset keyed by bioguide ID instead.
        Only current memberships are available (no historical per-congress data).
        """
        logger.info("Congress API: fetching committee metadata (unitedstates/congress-legislators)")
        resp = self._session.get(f"{self._LEGISLATORS_BASE}/committees-current.yaml", timeout=30)
        resp.raise_for_status()
        committees_raw = yaml.safe_load(resp.text)

        # Build lookup: code -> {name, chamber} for both parents and subcommittees
        committee_info: dict[str, dict] = {}
        for c in committees_raw:
            tid = c.get("thomas_id", "")
            committee_info[tid] = {"name": c.get("name", ""), "chamber": c.get("type", "")}
            for sub in c.get("subcommittees", []):
                sub_code = tid + sub.get("thomas_id", "")
                committee_info[sub_code] = {
                    "name": sub.get("name", ""),
                    "chamber": c.get("type", ""),
                    "parent_id": tid,
                    "parent_name": c.get("name", ""),
                }

        logger.info("Congress API: fetching committee membership data")
        resp = self._session.get(
            f"{self._LEGISLATORS_BASE}/committee-membership-current.yaml", timeout=30
        )
        resp.raise_for_status()
        memberships_raw: dict = yaml.safe_load(resp.text)

        records: list[dict] = []
        for code, members in memberships_raw.items():
            info = committee_info.get(code, {})
            parent_id = info.get("parent_id")
            for m in members:
                bioguide_id = m.get("bioguide")
                if not bioguide_id:
                    continue
                records.append({
                    "bioguide_id": bioguide_id,
                    "congress": congress,
                    "chamber": info.get("chamber", ""),
                    "committee_code": parent_id or code,
                    "committee_name": (
                        info.get("parent_name", "") if parent_id else info.get("name", "")
                    ),
                    "subcommittee_code": code if parent_id else None,
                    "subcommittee_name": info.get("name", "") if parent_id else None,
                    "rank": m.get("rank"),
                    "title": m.get("title"),
                    "party": m.get("party"),
                })

        logger.info("Congress API: fetched %d committee membership rows", len(records))
        return records

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
        year1, year2 = congress_years(congress)

        logger.info("Congress API: fetching members congress=%d", congress)
        members = self.get_members(congress=congress)

        logger.info(
            "Congress API: fetching committees and member assignments congress=%d", congress
        )
        house_committees = self.get_committees(chamber="house")
        senate_committees = self.get_committees(chamber="senate")
        committee_memberships = self.get_committee_memberships(congress=congress)

        logger.info("Congress API: fetching bills congress=%d", congress)
        bills = self.get_all_bills(congress)

        logger.info("Congress API: fetching sponsored legislation for %d members", len(members))
        member_sponsorships = self.get_all_member_sponsorships(members)

        # House votes are indexed by year; each congress spans two calendar years.
        logger.info("Congress API: fetching House votes years=%d,%d", year1, year2)
        house_votes = self.get_house_votes(year=year1) + self.get_house_votes(year=year2)

        # Senate votes are indexed by congress + session (two sessions per congress).
        logger.info("Congress API: fetching Senate votes congress=%d sessions=1,2", congress)
        senate_votes = (
            self.get_senate_votes(congress=congress, session=1)
            + self.get_senate_votes(congress=congress, session=2)
        )

        return {
            "members": members,
            "house_committees": house_committees,
            "senate_committees": senate_committees,
            "congress_committee_memberships": committee_memberships,
            "congress_bills": bills,
            "congress_member_sponsorships": member_sponsorships,
            "congress_house_votes": house_votes,
            "congress_senate_votes": senate_votes,
        }
