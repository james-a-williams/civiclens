from fastapi.testclient import TestClient

from src.api import main

client = TestClient(main.app)

MEMBER_ROW = {
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
    "committees": [],
}

FINANCE_ROW = {
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

CONFLICT_ROW = {
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
        "Sits on: Senate Finance. These committees oversee: Finance / Insurance / Real Estate."
    ),
}

BILL_ROW = {
    "bill_key": "bk1",
    "source_system": "congress",
    "level": "federal",
    "state": None,
    "congress": 119,
    "session": None,
    "bill_type": "s",
    "identifier": "S. 100",
    "title": "A bill to do things",
    "abstract": None,
    "url": None,
    "latest_action_date": "2025-01-15",
    "latest_action_text": "Referred to committee.",
    "update_date": "2025-01-15",
    "plain_summary": None,
    "eli5": None,
    "model_id": None,
    "generated_at": None,
    "summary_status": "none",
}


def _fake_query(responses):
    calls = []

    def fake(sql, params=None):
        calls.append((sql, params))
        for fragment, rows in responses.items():
            if fragment in sql:
                return rows
        return []

    fake.calls = calls
    return fake


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


# ── Member search ──────────────────────────────────────────────────────────────

def test_search_returns_results_and_total(monkeypatch):
    row = {**MEMBER_ROW, "total_count": 12}
    monkeypatch.setattr(main.db, "query", _fake_query({"from dim_members": [row]}))
    resp = client.get("/members", params={"q": "wyden", "chamber": "senate"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 12
    assert body["results"][0]["name"] == "Ron Wyden"
    assert "total_count" not in body["results"][0]


def test_search_uppercases_state(monkeypatch):
    fake = _fake_query({})
    monkeypatch.setattr(main.db, "query", fake)
    client.get("/members", params={"state": "or"})
    assert fake.calls[0][1]["state"] == "OR"


def test_search_rejects_bad_chamber():
    assert client.get("/members", params={"chamber": "galactic"}).status_code == 422


# ── Member profile ─────────────────────────────────────────────────────────────

def test_profile_returns_member_and_committees(monkeypatch):
    committees = [{"committee_name": "Senate Finance", "role_title": "Member",
                   "rank": 3, "industry_category": "Finance", "congress": 119}]
    monkeypatch.setattr(main.db, "query", _fake_query({
        "from dim_members": [MEMBER_ROW],
        "from fct_committee_memberships": committees,
    }))
    resp = client.get("/members/mk1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Ron Wyden"
    assert body["committees"][0]["committee_name"] == "Senate Finance"


def test_profile_404(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({}))
    assert client.get("/members/nope").status_code == 404


# ── Finance ────────────────────────────────────────────────────────────────────

def test_finance_returns_cycles(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({
        "from dim_members": [MEMBER_ROW],
        "from fct_member_finance": [FINANCE_ROW],
    }))
    resp = client.get("/members/mk1/finance")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cycles"][0]["pac_pct_of_total"] == "36.0"


def test_finance_404(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({}))
    assert client.get("/members/nope/finance").status_code == 404


# ── Legislative record ─────────────────────────────────────────────────────────

def test_record_returns_sponsored_and_votes(monkeypatch):
    sponsored = [{"bill_key": "bk1", "identifier": "S. 100", "title": "A bill",
                  "is_primary": True, "introduced_date": "2025-01-01",
                  "abstract": None, "url": None}]
    votes = [{"bill_key": "bk1", "identifier": "S. 100", "title": "A bill",
               "vote_event_id": "senate:119:1:1", "vote_date": "2025-02-01",
               "vote_option": "yes", "vote_result": "pass",
               "motion_text": "Passage", "plain_summary": None, "eli5": None}]
    monkeypatch.setattr(main.db, "query", _fake_query({
        "from dim_members": [MEMBER_ROW],
        "from fct_bill_sponsorships": sponsored,
        "from fct_votes": votes,
    }))
    resp = client.get("/members/mk1/record")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sponsored"][0]["identifier"] == "S. 100"
    assert body["votes"][0]["vote_option"] == "yes"


def test_record_404(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({}))
    assert client.get("/members/nope/record").status_code == 404


# ── Conflict of interest ───────────────────────────────────────────────────────

def test_conflict_returns_score_and_evidence(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({
        "from dim_members": [MEMBER_ROW],
        "from mart_conflict_of_interest": [CONFLICT_ROW],
    }))
    resp = client.get("/members/mk1/conflict")
    assert resp.status_code == 200
    body = resp.json()
    assert body["latest"]["risk_level"] == "Medium"
    assert body["latest"]["coi_score"] == "36.0"
    assert "PACs" in body["latest"]["evidence_description"]
    assert len(body["history"]) == 1


def test_conflict_no_data_returns_null_latest(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({
        "from dim_members": [MEMBER_ROW],
    }))
    resp = client.get("/members/mk1/conflict")
    assert resp.status_code == 200
    assert resp.json()["latest"] is None


def test_conflict_404(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({}))
    assert client.get("/members/nope/conflict").status_code == 404


# ── Bill endpoints ─────────────────────────────────────────────────────────────

def test_get_bill(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({"from dim_bills": [BILL_ROW]}))
    resp = client.get("/bills/bk1")
    assert resp.status_code == 200
    assert resp.json()["identifier"] == "S. 100"


def test_get_bill_404(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({}))
    assert client.get("/bills/nope").status_code == 404


class _FakeClaude:
    class _FakeMessages:
        def create(self, **kwargs):
            class _Resp:
                content = [
                    type("C", (), {
                        "text": '{"plain_summary": "It does things.", "eli5": "Simple."}'
                    })()
                ]
            return _Resp()
    messages = _FakeMessages()


def test_summarize_generates_summary(monkeypatch):
    executes = []
    monkeypatch.setattr(main.db, "query", _fake_query({"from dim_bills": [BILL_ROW]}))
    monkeypatch.setattr(main.db, "execute", lambda sql, params=None: executes.append(sql))
    monkeypatch.setattr(main, "_get_claude", lambda: _FakeClaude())
    resp = client.post("/bills/bk1/summarize")
    assert resp.status_code == 200
    assert resp.json()["plain_summary"] == "It does things."
    assert any("insert into app.bill_summaries" in s.lower() for s in executes)


def test_summarize_404(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({}))
    assert client.post("/bills/nope/summarize").status_code == 404
