import pytest
import requests
import responses as rsps

from src.connectors.census import CensusConnector

BASE = "https://api.census.gov/data"


@pytest.fixture
def connector():
    return CensusConnector(api_key="test-key")


SAMPLE_RESPONSE = [
    ["NAME", "B01003_001E", "B19013_001E", "state", "congressional district"],
    ["Congressional District 1, California", "750000", "85000", "06", "01"],
    ["Congressional District 2, California", "720000", "72000", "06", "02"],
]


@rsps.activate
def test_get_congressional_districts_returns_records(connector):
    rsps.add(rsps.GET, f"{BASE}/2023/acs/acs5", json=SAMPLE_RESPONSE)
    districts = connector.get_congressional_districts()
    assert len(districts) == 2
    assert districts[0]["total_population"] == "750000"
    assert districts[0]["median_household_income"] == "85000"


@rsps.activate
def test_variable_names_are_remapped(connector):
    rsps.add(rsps.GET, f"{BASE}/2023/acs/acs5", json=SAMPLE_RESPONSE)
    districts = connector.get_congressional_districts()
    assert "total_population" in districts[0]
    assert "B01003_001E" not in districts[0]


@rsps.activate
def test_get_congressional_districts_auth_error(connector):
    rsps.add(rsps.GET, f"{BASE}/2023/acs/acs5", status=401)
    with pytest.raises(requests.HTTPError):
        connector.get_congressional_districts()


@rsps.activate
def test_get_state_demographics_returns_records(connector):
    state_response = [
        ["NAME", "B01003_001E", "B19013_001E", "state"],
        ["California", "39500000", "78000", "06"],
    ]
    rsps.add(rsps.GET, f"{BASE}/2023/acs/acs5", json=state_response)
    states = connector.get_state_demographics()
    assert len(states) == 1
    assert states[0]["NAME"] == "California"


@rsps.activate
def test_fetch_all_returns_expected_keys(connector):
    rsps.add(rsps.GET, f"{BASE}/2023/acs/acs5", json=SAMPLE_RESPONSE)
    rsps.add(rsps.GET, f"{BASE}/2023/acs/acs5", json=SAMPLE_RESPONSE)
    result = connector.fetch_all()
    assert set(result.keys()) == {"congressional_districts", "states"}


@rsps.activate
def test_api_key_not_in_records(connector):
    rsps.add(rsps.GET, f"{BASE}/2023/acs/acs5", json=SAMPLE_RESPONSE)
    districts = connector.get_congressional_districts()
    assert "key" not in districts[0]
