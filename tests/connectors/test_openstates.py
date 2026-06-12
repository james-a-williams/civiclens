import pytest
import requests
import responses as rsps

from src.connectors.openstates import OpenStatesConnector

BASE = "https://v3.openstates.org"


@pytest.fixture
def connector():
    return OpenStatesConnector(api_key="test-key")


@rsps.activate
def test_get_people_returns_records(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/people",
        json={
            "results": [{"id": "ocd-person/123", "name": "Jane Smith", "party": "Democratic"}],
            "pagination": {"page": 1, "max_page": 1, "per_page": 20, "total_items": 1},
        },
    )
    people = connector.get_people("ca")
    assert len(people) == 1
    assert people[0]["name"] == "Jane Smith"


@rsps.activate
def test_get_people_paginates(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/people",
        json={
            "results": [{"id": "ocd-person/1", "name": "A"}],
            "pagination": {"page": 1, "max_page": 2, "per_page": 20, "total_items": 2},
        },
    )
    rsps.add(
        rsps.GET,
        f"{BASE}/people",
        json={
            "results": [{"id": "ocd-person/2", "name": "B"}],
            "pagination": {"page": 2, "max_page": 2, "per_page": 20, "total_items": 2},
        },
    )
    people = connector.get_people("ca")
    assert len(people) == 2


@rsps.activate
def test_get_people_empty(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/people",
        json={
            "results": [],
            "pagination": {"page": 1, "max_page": 1, "per_page": 20, "total_items": 0},
        },
    )
    assert connector.get_people("ca") == []


@rsps.activate
def test_get_people_auth_error(connector):
    rsps.add(rsps.GET, f"{BASE}/people", status=401)
    with pytest.raises(requests.HTTPError):
        connector.get_people("ca")


@rsps.activate
def test_get_bills_returns_records(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/bills",
        json={
            "results": [{"id": "ocd-bill/123", "title": "Test Bill"}],
            "pagination": {"page": 1, "max_page": 1, "per_page": 20, "total_items": 1},
        },
    )
    bills = connector.get_bills("ca")
    assert len(bills) == 1
    assert bills[0]["title"] == "Test Bill"


@rsps.activate
def test_api_key_sent_in_header(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/people",
        json={
            "results": [],
            "pagination": {"page": 1, "max_page": 1, "per_page": 20, "total_items": 0},
        },
    )
    connector.get_people("ca")
    assert rsps.calls[0].request.headers.get("X-API-Key") == "test-key"
