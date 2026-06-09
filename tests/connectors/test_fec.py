import pytest
import requests
import responses as rsps

from src.connectors.fec import FECConnector

BASE = "https://api.open.fec.gov/v1"


@pytest.fixture
def connector():
    return FECConnector(api_key="test-key")


@rsps.activate
def test_get_candidates_returns_records(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/candidates/search",
        json={
            "results": [{"candidate_id": "P00000001", "name": "Jane Smith"}],
            "pagination": {"page": 1, "pages": 1},
        },
    )
    candidates = connector.get_candidates(cycle=2024)
    assert len(candidates) == 1
    assert candidates[0]["candidate_id"] == "P00000001"


@rsps.activate
def test_get_candidates_empty(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/candidates/search",
        json={"results": [], "pagination": {"page": 1, "pages": 1}},
    )
    assert connector.get_candidates() == []


@rsps.activate
def test_get_candidates_auth_error(connector):
    rsps.add(rsps.GET, f"{BASE}/candidates/search", status=403)
    with pytest.raises(requests.HTTPError):
        connector.get_candidates()


@rsps.activate
def test_get_candidate_not_found_raises(connector):
    rsps.add(rsps.GET, f"{BASE}/candidate/INVALID", json={"results": []})
    from src.connectors.base import ConnectorError
    with pytest.raises(ConnectorError):
        connector.get_candidate("INVALID")


@rsps.activate
def test_get_committees_returns_records(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/committees",
        json={
            "results": [{"committee_id": "C00000001", "name": "Test PAC"}],
            "pagination": {"page": 1, "pages": 1},
        },
    )
    committees = connector.get_committees(cycle=2024)
    assert len(committees) == 1


@rsps.activate
def test_fetch_all_returns_expected_keys(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/candidates/search",
        json={"results": [], "pagination": {"page": 1, "pages": 1}},
    )
    rsps.add(
        rsps.GET,
        f"{BASE}/committees",
        json={"results": [], "pagination": {"page": 1, "pages": 1}},
    )
    result = connector.fetch_all(cycle=2024)
    assert set(result.keys()) == {"candidates", "committees"}
