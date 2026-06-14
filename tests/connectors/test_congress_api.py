import pytest
import requests
import responses as rsps

from src.connectors.congress_api import (
    BILL_TYPES,
    CONGRESS_RANGE,
    CongressAPIConnector,
    congress_years,
)

BASE = "https://api.congress.gov/v3"
CLERK = "https://clerk.house.gov/evs"
SENATE = "https://www.senate.gov/legislative/LIS/roll_call_votes"


@pytest.fixture
def connector():
    return CongressAPIConnector(api_key="test-key")


def test_congress_years_maps_correctly():
    assert congress_years(111) == (2009, 2010)
    assert congress_years(119) == (2025, 2026)
    assert congress_years(118) == (2023, 2024)


def test_congress_range_starts_at_111_and_includes_current():
    assert CONGRESS_RANGE[0] == 111
    assert 119 in CONGRESS_RANGE


@rsps.activate
def test_get_members_returns_records(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/member",
        json={
            "members": [{"bioguideId": "A000001", "name": "Jane Smith"}],
            "pagination": {"next": None},
        },
    )
    members = connector.get_members(congress=119)
    assert len(members) == 1
    assert members[0]["bioguideId"] == "A000001"


@rsps.activate
def test_get_members_paginates(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/member",
        json={
            "members": [{"bioguideId": "A000001"}],
            "pagination": {"next": f"{BASE}/member?offset=1"},
        },
    )
    rsps.add(
        rsps.GET,
        f"{BASE}/member",
        json={"members": [{"bioguideId": "A000002"}], "pagination": {"next": None}},
    )
    members = connector.get_members(congress=119)
    assert len(members) == 2


@rsps.activate
def test_get_members_empty(connector):
    rsps.add(
        rsps.GET, f"{BASE}/member", json={"members": [], "pagination": {"next": None}}
    )
    members = connector.get_members(congress=119)
    assert members == []


@rsps.activate
def test_get_members_auth_error(connector):
    rsps.add(rsps.GET, f"{BASE}/member", status=403)
    with pytest.raises(requests.HTTPError):
        connector.get_members(congress=119)


@rsps.activate
def test_get_member_not_found_raises(connector):
    rsps.add(rsps.GET, f"{BASE}/member/X000000", json={"member": None})
    from src.connectors.base import ConnectorError
    with pytest.raises(ConnectorError):
        connector.get_member("X000000")


LEGISLATORS_BASE = (
    "https://raw.githubusercontent.com/unitedstates/congress-legislators/refs/heads/main"
)

_COMMITTEES_YAML = """
- thomas_id: SSFI
  name: Senate Committee on Finance
  type: senate
  subcommittees:
    - thomas_id: "01"
      name: Health Care Subcommittee
- thomas_id: HSWM
  name: House Committee on Ways and Means
  type: house
"""

_MEMBERSHIPS_YAML = """
SSFI:
  - bioguide: W000779
    rank: 1
    title: Ranking Member
    party: minority
  - bioguide: C000141
    rank: 2
    party: minority
SSFI01:
  - bioguide: W000779
    rank: 1
    party: minority
HSWM:
  - bioguide: S000051
    rank: 1
    title: Chairman
    party: majority
"""


@rsps.activate
def test_get_committee_memberships_returns_flat_records(connector):
    rsps.add(rsps.GET, f"{LEGISLATORS_BASE}/committees-current.yaml", body=_COMMITTEES_YAML)
    rsps.add(rsps.GET, f"{LEGISLATORS_BASE}/committee-membership-current.yaml", body=_MEMBERSHIPS_YAML)

    memberships = connector.get_committee_memberships(congress=119)

    assert len(memberships) == 4  # 2 SSFI + 1 SSFI01 (subcom) + 1 HSWM
    senate = [m for m in memberships if m["chamber"] == "senate"]
    house = [m for m in memberships if m["chamber"] == "house"]
    assert len(senate) == 3
    assert len(house) == 1

    # Full committee rows
    ssfi_rows = [m for m in memberships if m["committee_code"] == "SSFI" and m["subcommittee_code"] is None]
    assert len(ssfi_rows) == 2
    first = ssfi_rows[0]
    assert first["bioguide_id"] == "W000779"
    assert first["committee_name"] == "Senate Committee on Finance"
    assert first["congress"] == 119
    assert first["rank"] == 1
    assert first["title"] == "Ranking Member"


@rsps.activate
def test_get_committee_memberships_maps_subcommittees(connector):
    rsps.add(rsps.GET, f"{LEGISLATORS_BASE}/committees-current.yaml", body=_COMMITTEES_YAML)
    rsps.add(rsps.GET, f"{LEGISLATORS_BASE}/committee-membership-current.yaml", body=_MEMBERSHIPS_YAML)

    memberships = connector.get_committee_memberships(congress=119)

    sub_rows = [m for m in memberships if m["subcommittee_code"] is not None]
    assert len(sub_rows) == 1
    sub = sub_rows[0]
    assert sub["committee_code"] == "SSFI"
    assert sub["committee_name"] == "Senate Committee on Finance"
    assert sub["subcommittee_code"] == "SSFI01"
    assert sub["subcommittee_name"] == "Health Care Subcommittee"


@rsps.activate
def test_get_committee_memberships_skips_missing_bioguide(connector):
    memberships_with_gap = _MEMBERSHIPS_YAML + "  - rank: 3\n    party: minority\n"
    rsps.add(rsps.GET, f"{LEGISLATORS_BASE}/committees-current.yaml", body=_COMMITTEES_YAML)
    rsps.add(rsps.GET, f"{LEGISLATORS_BASE}/committee-membership-current.yaml", body=memberships_with_gap)

    memberships = connector.get_committee_memberships(congress=119)
    bioguides = [m["bioguide_id"] for m in memberships]
    assert None not in bioguides


@rsps.activate
def test_fetch_all_returns_expected_keys(connector):
    empty_members = {"members": [], "pagination": {"next": None}}
    empty_committees = {"committees": [], "pagination": {"next": None}}
    empty_bills = {"bills": [], "pagination": {"next": None}}

    rsps.add(rsps.GET, f"{BASE}/member", json=empty_members)
    rsps.add(rsps.GET, f"{BASE}/committee/house", json=empty_committees)
    rsps.add(rsps.GET, f"{BASE}/committee/senate", json=empty_committees)

    # get_committee_memberships now fetches from unitedstates/congress-legislators
    rsps.add(rsps.GET, f"{LEGISLATORS_BASE}/committees-current.yaml", body=_COMMITTEES_YAML)
    rsps.add(rsps.GET, f"{LEGISLATORS_BASE}/committee-membership-current.yaml", body=_MEMBERSHIPS_YAML)

    # Bill endpoints — one per bill type
    for bill_type in BILL_TYPES:
        rsps.add(rsps.GET, f"{BASE}/bill/119/{bill_type}", json=empty_bills)

    # House Clerk — 404 for both years of the 119th Congress (2025, 2026)
    rsps.add(rsps.GET, f"{CLERK}/2025/roll001.xml", status=404)
    rsps.add(rsps.GET, f"{CLERK}/2026/roll001.xml", status=404)
    # Senate LIS — 404 for both sessions
    rsps.add(rsps.GET, f"{SENATE}/vote1191/vote_119_1_00001.xml", status=404)
    rsps.add(rsps.GET, f"{SENATE}/vote1192/vote_119_2_00001.xml", status=404)

    result = connector.fetch_all(congress=119)
    assert set(result.keys()) == {
        "members",
        "house_committees",
        "senate_committees",
        "congress_committee_memberships",
        "congress_bills",
        "congress_member_sponsorships",
        "congress_house_votes",
        "congress_senate_votes",
    }
