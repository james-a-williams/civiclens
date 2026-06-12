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
def test_get_candidate_totals_returns_records(connector):
    rsps.add(
        rsps.GET,
        f"{BASE}/candidates/totals",
        json={
            "results": [
                {
                    "candidate_id": "H4MN03159",
                    "cycle": 2024,
                    "receipts": 150000.0,
                    "disbursements": 120000.0,
                    "last_cash_on_hand_end_period": 30000.0,
                }
            ],
            "pagination": {"page": 1, "pages": 1},
        },
    )
    totals = connector.get_candidate_totals(cycle=2024)
    assert len(totals) == 1
    assert totals[0]["receipts"] == 150000.0


@rsps.activate
def test_fetch_all_returns_expected_keys(connector):
    empty = {"results": [], "pagination": {"page": 1, "pages": 1}}
    rsps.add(rsps.GET, f"{BASE}/candidates/search", json=empty)
    rsps.add(rsps.GET, f"{BASE}/committees", json=empty)
    rsps.add(rsps.GET, f"{BASE}/candidates/totals", json=empty)
    result = connector.fetch_all(cycle=2024)
    assert set(result.keys()) == {"candidates", "committees", "candidate_totals"}
