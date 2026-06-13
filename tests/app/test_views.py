"""Streamlit AppTest smoke tests.

The views import api_client (which lives next to the app entrypoint), so the
tests pre-register a stub module under that name — the views never touch the
network or Snowflake.
"""

import sys
import types

import pytest
from streamlit.testing.v1 import AppTest

SEARCH_RESPONSE = {
    "results": [
        {
            "candidacy_key": "abc123",
            "display_name": "Jane Smith",
            "party": "Democratic Party",
            "level": "federal",
            "office": "House",
            "state": "NY",
            "district": 14,
            "cycle": 2024,
            "is_incumbent": True,
            "source_system": "fec",
        }
    ],
    "total": 1,
    "limit": 25,
    "offset": 0,
}

PROFILE_RESPONSE = {
    "candidacy_key": "abc123",
    "person_key": "p1",
    "display_name": "Jane Smith",
    "party": "Democratic Party",
    "level": "federal",
    "office": "House",
    "state": "NY",
    "district": 14,
    "cycle": 2024,
    "incumbent_challenge": "I",
    "is_incumbent": True,
    "source_system": "fec",
    "source_id": "H0NY14000",
    "other_candidacies": [],
    "district_context": {
        "district_key": "cd-36-14",
        "geo_level": "congressional_district",
        "name": "Congressional District 14, New York",
        "total_population": 720139,
        "median_household_income": 68421,
        "pct_white": "0.253",
        "pct_black": "0.190",
        "pct_hispanic": "0.519",
        "pct_bachelors": "0.126",
        "pct_insured": "0.988",
    },
}

FINANCE_RESPONSE = {
    "summary": {
        "coverage": "nyc_cfb",
        "total_raised": "4096067.00",
        "total_spent": None,
        "cash_on_hand": None,
        "public_funds_received": None,
        "matchable_amount_total": 1646987,
        "contribution_count": 54138,
        "unique_donor_count": 42896,
        "avg_contribution": "75.66",
        "pct_small_dollar": "0.480",
    },
    "top_donors": [
        {
            "contributor_name": "Big Donor",
            "employer_name": "Acme",
            "city": "Brooklyn",
            "state": "NY",
            "total_amount": 6300,
            "contribution_count": 6,
        }
    ],
    "top_employers": [
        {"employer_name": "Acme", "total_amount": 631097, "contribution_count": 6272}
    ],
    "geo_breakdown": [
        {"city": "BROOKLYN", "state": "NY", "total_amount": 1155668, "contribution_count": 16384}
    ],
}


@pytest.fixture
def stub_api(monkeypatch):
    stub = types.ModuleType("api_client")

    def get(path, **params):
        if path == "/candidates":
            return SEARCH_RESPONSE
        if path.endswith("/finance"):
            return FINANCE_RESPONSE
        return PROFILE_RESPONSE

    stub.get = get
    stub.to_float = lambda v: None if v is None else float(v)
    monkeypatch.setitem(sys.modules, "api_client", stub)
    return stub


def test_find_candidates_renders_results(stub_api):
    at = AppTest.from_file("src/app/views/find_candidates.py").run()
    assert not at.exception
    assert any("1" in md.value and "found" in md.value for md in at.markdown)
    assert len(at.dataframe) == 1


def test_profile_renders_overview_and_finance(stub_api):
    at = AppTest.from_file("src/app/views/profile.py")
    at.session_state["candidacy_key"] = "abc123"
    at.run()
    assert not at.exception
    assert at.title[0].value == "Jane Smith"
    metric_labels = {m.label for m in at.metric}
    assert "Population" in metric_labels
    assert "Total raised" in metric_labels
    raised = next(m for m in at.metric if m.label == "Total raised")
    assert raised.value == "$4,096,067"


def test_profile_without_selection_shows_hint(stub_api):
    at = AppTest.from_file("src/app/views/profile.py").run()
    assert not at.exception
    assert at.info
