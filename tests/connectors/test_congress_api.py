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


@rsps.activate
def test_get_committee_members_returns_flat_records(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/committee/119/senate/SSFI",
        json={
            "committee": {
                "systemCode": "SSFI",
                "name": "Senate Committee on Finance",
                "currentMembers": [
                    {"bioguideId": "W000779", "rank": 1, "title": "Ranking Member"},
                    {"bioguideId": "C000141", "rank": 2, "title": "Member"},
                ],
            }
        },
    )
    members = connector.get_committee_members("senate", "SSFI", congress=119)
    assert len(members) == 2
    assert members[0]["bioguide_id"] == "W000779"
    assert members[0]["committee_name"] == "Senate Committee on Finance"
    assert members[0]["chamber"] == "senate"
    assert members[0]["congress"] == 119
    assert members[0]["subcommittee_code"] is None


@rsps.activate
def test_get_committee_members_skips_missing_bioguide(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/committee/119/house/HSWM",
        json={
            "committee": {
                "name": "House Ways and Means",
                "currentMembers": [
                    {"bioguideId": "S000051", "rank": 1},
                    {"rank": 2},  # no bioguideId — should be skipped
                ],
            }
        },
    )
    members = connector.get_committee_members("house", "HSWM", congress=119)
    assert len(members) == 1


@rsps.activate
def test_get_committee_memberships_iterates_both_chambers(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/committee/house",
        json={
            "committees": [{"systemCode": "HSWM", "name": "Ways and Means"}],
            "pagination": {"next": None},
        },
    )
    rsps.add(
        rsps.GET,
        f"{BASE}/committee/senate",
        json={
            "committees": [{"systemCode": "SSFI", "name": "Senate Finance"}],
            "pagination": {"next": None},
        },
    )
    rsps.add(
        rsps.GET,
        f"{BASE}/committee/119/house/HSWM",
        json={
            "committee": {
                "name": "Ways and Means",
                "currentMembers": [{"bioguideId": "S000051", "rank": 1}],
            }
        },
    )
    rsps.add(
        rsps.GET,
        f"{BASE}/committee/119/senate/SSFI",
        json={
            "committee": {
                "name": "Senate Finance",
                "currentMembers": [{"bioguideId": "W000779", "rank": 1}],
            }
        },
    )
    memberships = connector.get_committee_memberships(congress=119)
    assert len(memberships) == 2
    chambers = {m["chamber"] for m in memberships}
    assert chambers == {"house", "senate"}


@rsps.activate
def test_get_committee_memberships_skips_failed_committee(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/committee/house",
        json={
            "committees": [
                {"systemCode": "HSWM"},
                {"systemCode": "HSAS"},
            ],
            "pagination": {"next": None},
        },
    )
    rsps.add(rsps.GET, f"{BASE}/committee/senate",
             json={"committees": [], "pagination": {"next": None}})
    rsps.add(rsps.GET, f"{BASE}/committee/119/house/HSWM", status=500)
    rsps.add(
        rsps.GET,
        f"{BASE}/committee/119/house/HSAS",
        json={
            "committee": {
                "name": "Armed Services",
                "currentMembers": [{"bioguideId": "S000051", "rank": 1}],
            }
        },
    )
    memberships = connector.get_committee_memberships(congress=119)
    # HSWM failed (500) but HSAS succeeded — should get 1 record, not raise
    assert len(memberships) == 1
    assert memberships[0]["committee_code"] == "HSAS"


@rsps.activate
def test_fetch_all_returns_expected_keys(connector):
    empty_members = {"members": [], "pagination": {"next": None}}
    empty_committees = {"committees": [], "pagination": {"next": None}}
    empty_bills = {"bills": [], "pagination": {"next": None}}

    rsps.add(rsps.GET, f"{BASE}/member", json=empty_members)
    rsps.add(rsps.GET, f"{BASE}/committee/house", json=empty_committees)
    rsps.add(rsps.GET, f"{BASE}/committee/senate", json=empty_committees)

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
