"""Streamlit AppTest smoke tests for the federal-officials scope.

Views import api_client (lives next to the app entrypoint), so tests
pre-register a stub module — views never touch the network or Snowflake.
"""

import sys
import types

import pytest
from streamlit.testing.v1 import AppTest

SEARCH_RESPONSE = {
    "results": [
        {
            "member_key": "mk1",
            "bioguide_id": "W000779",
            "name": "Ron Wyden",
            "display_name": "Senator Ron Wyden (D-OR)",
            "party": "Democratic Party",
            "chamber": "senate",
            "state": "OR",
            "district": None,
            "latest_congress": 119,
        }
    ],
    "total": 1,
    "limit": 25,
    "offset": 0,
}

PROFILE_RESPONSE = {
    "member_key": "mk1",
    "bioguide_id": "W000779",
    "fec_candidate_id": "S6OR00163",
    "name": "Ron Wyden",
    "display_name": "Senator Ron Wyden (D-OR)",
    "party": "Democratic Party",
    "state": "OR",
    "chamber": "senate",
    "district": None,
    "title": "Senator",
    "latest_congress": 119,
    "updated_at": "2025-01-01",
    "committees": [
        {
            "committee_name": "Senate Finance",
            "role_title": "Ranking Member",
            "rank": 2,
            "industry_category": "Finance / Insurance / Real Estate",
            "congress": 119,
        }
    ],
}

FINANCE_RESPONSE = {
    "member_key": "mk1",
    "cycles": [
        {
            "cycle": 2024,
            "total_receipts": "5000000.00",
            "total_disbursements": "4800000.00",
            "cash_on_hand": "200000.00",
            "individual_itemized_contributions": "2500000.00",
            "individual_unitemized_contributions": "500000.00",
            "pac_contributions": "1800000.00",
            "party_contributions": "100000.00",
            "candidate_self_funding": "100000.00",
            "pac_pct_of_total": "36.0",
            "individual_pct_of_total": "60.0",
        }
    ],
}

RECORD_RESPONSE = {
    "member_key": "mk1",
    "sponsored": [
        {
            "bill_key": "bk1",
            "identifier": "S. 100",
            "title": "A bill to do things",
            "abstract": None,
            "url": None,
            "is_primary": True,
            "introduced_date": "2025-01-10",
        }
    ],
    "votes": [
        {
            "bill_key": "bk1",
            "identifier": "S. 100",
            "title": "A bill to do things",
            "vote_event_id": "senate:119:1:1",
            "vote_date": "2025-02-01",
            "vote_option": "yes",
            "vote_result": "pass",
            "motion_text": "Passage",
            "plain_summary": None,
            "eli5": None,
        }
    ],
}

CONFLICT_RESPONSE = {
    "member_key": "mk1",
    "latest": {
        "cycle": 2024,
        "coi_score": "36.0",
        "risk_level": "Medium",
        "total_receipts": "5000000.00",
        "pac_contributions": "1800000.00",
        "individual_itemized_contributions": "2500000.00",
        "individual_unitemized_contributions": "500000.00",
        "party_contributions": "100000.00",
        "candidate_self_funding": "100000.00",
        "committees_served": "Senate Finance",
        "regulated_industries": "Finance / Insurance / Real Estate",
        "evidence_description": (
            "Received $1,800,000 from PACs (36.0% of $5,000,000 total raised in 2024). "
            "Sits on: Senate Finance."
        ),
    },
    "history": [],
}


@pytest.fixture
def stub_api(monkeypatch):
    stub = types.ModuleType("api_client")

    def get(path, **params):
        if path == "/members":
            return SEARCH_RESPONSE
        if path.endswith("/finance"):
            return FINANCE_RESPONSE
        if path.endswith("/record"):
            return RECORD_RESPONSE
        if path.endswith("/conflict"):
            return CONFLICT_RESPONSE
        return PROFILE_RESPONSE

    stub.get = get
    stub.post = lambda path: {"summary_status": "ready"}
    stub.to_float = lambda v: None if v is None else float(v)
    monkeypatch.setitem(sys.modules, "api_client", stub)
    return stub


def test_find_members_renders_results(stub_api):
    at = AppTest.from_file("src/app/views/find_members.py").run()
    assert not at.exception
    assert any("1" in md.value and "found" in md.value for md in at.markdown)
    assert len(at.dataframe) == 1


def test_profile_renders_all_tabs(stub_api):
    at = AppTest.from_file("src/app/views/member_profile.py")
    at.session_state["member_key"] = "mk1"
    at.run()
    assert not at.exception
    assert at.title[0].value == "Ron Wyden"
    tab_labels = [t.label for t in at.tabs]
    assert "Overview" in tab_labels
    assert "Finance" in tab_labels
    assert "Record" in tab_labels
    assert "Conflict of Interest" in tab_labels


def test_profile_finance_shows_totals(stub_api):
    at = AppTest.from_file("src/app/views/member_profile.py")
    at.session_state["member_key"] = "mk1"
    at.run()
    assert not at.exception
    metric_labels = {m.label for m in at.metric}
    assert "Total raised" in metric_labels
    raised = next(m for m in at.metric if m.label == "Total raised")
    assert raised.value == "$5,000,000"


def test_profile_conflict_shows_score(stub_api):
    at = AppTest.from_file("src/app/views/member_profile.py")
    at.session_state["member_key"] = "mk1"
    at.run()
    assert not at.exception
    metric_labels = {m.label for m in at.metric}
    assert "Conflict of Interest Score" in metric_labels
    score = next(m for m in at.metric if m.label == "Conflict of Interest Score")
    assert "36.0" in score.value


def test_profile_without_selection_shows_hint(stub_api):
    at = AppTest.from_file("src/app/views/member_profile.py").run()
    assert not at.exception
    assert at.info
