import pytest
import requests
import responses as rsps

from src.connectors.congress_api import CongressAPIConnector

BASE = "https://api.congress.gov/v3"


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
    for path in ["/member", "/committee/house", "/committee/senate"]:
        rsps.add(
            rsps.GET,
            f"{BASE}{path}",
            json={
                list({"members": [], "committees": []}.keys())[0 if "member" in path else 1]: [],
                "pagination": {"next": None},
            },
        )
    rsps.add(rsps.GET, f"{BASE}/member", json={"members": [], "pagination": {"next": None}})
    rsps.add(rsps.GET, f"{BASE}/committee/house", json={"committees": [], "pagination": {"next": None}})
    rsps.add(rsps.GET, f"{BASE}/committee/senate", json={"committees": [], "pagination": {"next": None}})
    result = connector.fetch_all(congress=119)
    assert set(result.keys()) == {"members", "house_committees", "senate_committees"}
