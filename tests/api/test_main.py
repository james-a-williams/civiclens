from fastapi.testclient import TestClient

from src.api import main

client = TestClient(main.app)

CANDIDATE_ROW = {
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
}

FINANCE_ROW = {
    "coverage": "nyc_cfb",
    "total_raised": 500000.0,
    "total_spent": None,
    "cash_on_hand": None,
    "public_funds_received": None,
    "matchable_amount_total": 120000.0,
    "contribution_count": 900,
    "unique_donor_count": 650,
    "avg_contribution": 555.55,
    "pct_small_dollar": 0.4,
}


def _fake_query(responses):
    """Return a query() stub serving canned rows keyed by SQL fragment."""
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


def test_search_returns_results_and_total(monkeypatch):
    row = {**CANDIDATE_ROW, "total_count": 37}
    monkeypatch.setattr(main.db, "query", _fake_query({"from dim_candidates": [row]}))
    resp = client.get("/candidates", params={"q": "smith", "state": "ny"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 37
    assert body["results"][0]["display_name"] == "Jane Smith"
    assert "total_count" not in body["results"][0]


def test_search_uppercases_state(monkeypatch):
    fake = _fake_query({})
    monkeypatch.setattr(main.db, "query", fake)
    client.get("/candidates", params={"state": "ny"})
    assert fake.calls[0][1]["state"] == "NY"


def test_search_rejects_bad_level():
    assert client.get("/candidates", params={"level": "galactic"}).status_code == 422


def test_profile_includes_district_context(monkeypatch):
    fake = _fake_query(
        {
            "from dim_candidates\nwhere candidacy_key": [dict(CANDIDATE_ROW)],
            "from dim_candidates\nwhere person_key": [],
            "from dim_districts": [{"district_key": "cd-36-14", "name": "NY-14"}],
        }
    )
    monkeypatch.setattr(main.db, "query", fake)
    resp = client.get("/candidates/abc123")
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "Jane Smith"
    assert body["district_context"]["district_key"] == "cd-36-14"
    # House incumbent → congressional district demographics requested
    district_call = next(p for s, p in fake.calls if "dim_districts" in s)
    assert district_call["geo_level"] == "congressional_district"


def test_profile_404(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({}))
    assert client.get("/candidates/nope").status_code == 404


def test_finance_with_transactions(monkeypatch):
    fake = _fake_query(
        {
            "from fct_candidate_finance": [dict(FINANCE_ROW)],
            "group by donor_key": [{"contributor_name": "Big Donor", "total_amount": 9000}],
            "group by employer_name": [{"employer_name": "Acme", "total_amount": 5000}],
            "group by city, state": [{"city": "Brooklyn", "total_amount": 7000}],
        }
    )
    monkeypatch.setattr(main.db, "query", fake)
    body = client.get("/candidates/abc123/finance").json()
    assert body["summary"]["total_raised"] == 500000.0
    assert body["top_donors"][0]["contributor_name"] == "Big Donor"
    assert body["top_employers"][0]["employer_name"] == "Acme"
    assert body["geo_breakdown"][0]["city"] == "Brooklyn"


def test_finance_fec_coverage_skips_donor_queries(monkeypatch):
    fec_summary = {**FINANCE_ROW, "coverage": "fec"}
    fake = _fake_query({"from fct_candidate_finance": [fec_summary]})
    monkeypatch.setattr(main.db, "query", fake)
    body = client.get("/candidates/abc123/finance").json()
    assert body["summary"]["coverage"] == "fec"
    assert body["top_donors"] == []
    assert not any("fct_contributions" in sql for sql, _ in fake.calls)


def test_finance_no_rows_for_real_candidacy(monkeypatch):
    fake = _fake_query({"from dim_candidates\nwhere candidacy_key": [dict(CANDIDATE_ROW)]})
    monkeypatch.setattr(main.db, "query", fake)
    body = client.get("/candidates/abc123/finance").json()
    assert body["summary"] is None
    assert body["top_donors"] == []


def test_finance_404_for_unknown_candidacy(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({}))
    assert client.get("/candidates/nope/finance").status_code == 404


# ── Bill endpoints ────────────────────────────────────────────────────────────

BILL_ROW_NO_SUMMARY = {
    "bill_key": "bk1",
    "source_system": "openstates",
    "level": "state",
    "state": "NY",
    "congress": None,
    "session": "2023-2024",
    "bill_type": None,
    "identifier": "HB 1234",
    "title": "An Act to improve things",
    "abstract": "This bill improves many things.",
    "url": "https://openstates.org/ny/bills/1234",
    "latest_action_date": None,
    "latest_action_text": None,
    "update_date": "2024-01-15",
    "plain_summary": None,
    "eli5": None,
    "model_id": None,
    "generated_at": None,
    "summary_status": "none",
}

BILL_ROW_WITH_SUMMARY = {
    **BILL_ROW_NO_SUMMARY,
    "plain_summary": "This improves things for New Yorkers.",
    "eli5": "It makes things better.",
    "model_id": "claude-haiku-4-5-20251001",
    "generated_at": "2026-01-01T00:00:00Z",
    "summary_status": "ready",
}


class _FakeClaude:
    class _FakeMessages:
        def create(self, **kwargs):
            class _Resp:
                content = [
                    type("C", (), {"text": '{"plain_summary": "Generated summary.", "eli5": "Simple."}'})()
                ]
            return _Resp()

    messages = _FakeMessages()


def test_get_bill_no_summary(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({"from dim_bills": [BILL_ROW_NO_SUMMARY]}))
    resp = client.get("/bills/bk1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["identifier"] == "HB 1234"
    assert body["summary_status"] == "none"
    assert body["plain_summary"] is None


def test_get_bill_with_summary(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({"from dim_bills": [BILL_ROW_WITH_SUMMARY]}))
    resp = client.get("/bills/bk1")
    assert resp.status_code == 200
    assert resp.json()["summary_status"] == "ready"
    assert resp.json()["plain_summary"] == "This improves things for New Yorkers."


def test_get_bill_404(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({}))
    assert client.get("/bills/nope").status_code == 404


def test_summarize_generates_and_inserts(monkeypatch):
    executes = []
    monkeypatch.setattr(main.db, "query", _fake_query({"from dim_bills": [BILL_ROW_NO_SUMMARY]}))
    monkeypatch.setattr(main.db, "execute", lambda sql, params=None: executes.append((sql, params)))
    monkeypatch.setattr(main, "_get_claude", lambda: _FakeClaude())

    resp = client.post("/bills/bk1/summarize")
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary_status"] == "ready"
    assert body["plain_summary"] == "Generated summary."
    assert body["eli5"] == "Simple."
    assert any("insert into app.bill_summaries" in sql.lower() for sql, _ in executes)


def test_summarize_idempotent_when_ready(monkeypatch):
    executes = []
    monkeypatch.setattr(main.db, "query", _fake_query({"from dim_bills": [BILL_ROW_WITH_SUMMARY]}))
    monkeypatch.setattr(main.db, "execute", lambda sql, params=None: executes.append((sql, params)))
    monkeypatch.setattr(main, "_get_claude", lambda: _FakeClaude())

    resp = client.post("/bills/bk1/summarize")
    assert resp.status_code == 200
    assert resp.json()["summary_status"] == "ready"
    assert resp.json()["plain_summary"] == "This improves things for New Yorkers."
    assert executes == []  # no INSERT when summary already exists


def test_summarize_404(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({}))
    assert client.post("/bills/nope/summarize").status_code == 404


def test_record_returns_sponsored_and_votes(monkeypatch):
    sponsored = [{"bill_key": "bk1", "identifier": "HB 1234", "title": "An Act", "is_primary": True}]
    votes = [{"bill_key": "bk1", "vote_option": "yes", "vote_date": "2024-01-10"}]
    fake = _fake_query({
        "from fct_bill_sponsorships": sponsored,
        "from fct_votes": votes,
    })
    monkeypatch.setattr(main.db, "query", fake)
    resp = client.get("/candidates/abc123/record")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sponsored"][0]["identifier"] == "HB 1234"
    assert body["votes"][0]["vote_option"] == "yes"


def test_record_404_for_unknown_candidacy(monkeypatch):
    monkeypatch.setattr(main.db, "query", _fake_query({}))
    assert client.get("/candidates/nope/record").status_code == 404
