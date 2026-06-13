import pytest
import requests
import responses as rsps

from src.connectors.congress_api import BILL_TYPES, CongressAPIConnector

BASE = "https://api.congress.gov/v3"
CLERK = "https://clerk.house.gov/evs"
SENATE = "https://www.senate.gov/legislative/LIS/roll_call_votes"


@pytest.fixture
def connector():
    return CongressAPIConnector(api_key="test-key")


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

    # House Clerk and Senate LIS — 404 so the loops exit immediately
    rsps.add(rsps.GET, f"{CLERK}/2025/roll001.xml", status=404)
    rsps.add(rsps.GET, f"{SENATE}/vote1191/vote_119_1_00001.xml", status=404)

    result = connector.fetch_all(congress=119)
    assert set(result.keys()) == {
        "members",
        "house_committees",
        "senate_committees",
        "congress_bills",
        "congress_member_sponsorships",
        "congress_house_votes",
        "congress_senate_votes",
    }
