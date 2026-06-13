"""CivicLens API — federal official accountability dashboard.

Endpoints:
  GET  /members                        search elected federal officials
  GET  /members/{member_key}           profile: identity, committees, terms
  GET  /members/{member_key}/finance   FEC fundraising by cycle, PAC breakdown
  GET  /members/{member_key}/record    sponsored bills + votes
  GET  /members/{member_key}/conflict  COI score with evidence description
  GET  /bills/{bill_key}               bill detail with optional AI summary
  POST /bills/{bill_key}/summarize     generate Claude Haiku AI summary
"""

import json
import logging

import anthropic
import uvicorn
from fastapi import FastAPI, HTTPException, Query

from . import db

logger = logging.getLogger(__name__)

app = FastAPI(title="CivicLens API", version="0.2.0")

SUMMARIZE_MODEL = "claude-haiku-4-5-20251001"

_claude: anthropic.Anthropic | None = None


def _get_claude() -> anthropic.Anthropic:
    global _claude
    if _claude is None:
        _claude = anthropic.Anthropic()
    return _claude


# ── Member search ──────────────────────────────────────────────────────────────

SEARCH_SQL = """
select
    member_key, bioguide_id, name, display_name, party, state,
    chamber, district, title, latest_congress,
    count(*) over () as total_count
from dim_members
where (%(q)s is null or name ilike '%%' || %(q)s || '%%')
  and (%(chamber)s is null or chamber = %(chamber)s)
  and (%(state)s is null or state = %(state)s)
  and (%(party)s is null or party ilike '%%' || %(party)s || '%%')
  and (%(congress)s is null or latest_congress = %(congress)s)
order by name
limit %(limit)s offset %(offset)s
"""


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/members")
def search_members(
    q: str | None = None,
    chamber: str | None = Query(None, pattern="^(house|senate)$"),
    state: str | None = None,
    party: str | None = None,
    congress: int | None = None,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    rows = db.query(
        SEARCH_SQL,
        {
            "q": q,
            "chamber": chamber,
            "state": state.upper() if state else None,
            "party": party,
            "congress": congress,
            "limit": limit,
            "offset": offset,
        },
    )
    total = rows[0]["total_count"] if rows else 0
    for row in rows:
        row.pop("total_count", None)
    return {"results": rows, "total": total, "limit": limit, "offset": offset}


# ── Member profile ─────────────────────────────────────────────────────────────

PROFILE_SQL = """
select
    member_key, bioguide_id, fec_candidate_id, name, display_name,
    party, state, chamber, district, title, latest_congress, updated_at
from dim_members
where member_key = %(key)s
"""

COMMITTEES_SQL = """
select committee_name, role_title, rank, industry_category, congress
from fct_committee_memberships
where member_key = %(key)s
order by congress desc, rank asc nulls last
"""


@app.get("/members/{member_key}")
def member_profile(member_key: str) -> dict:
    rows = db.query(PROFILE_SQL, {"key": member_key})
    if not rows:
        raise HTTPException(status_code=404, detail="member not found")
    profile = rows[0]
    committees = db.query(COMMITTEES_SQL, {"key": member_key})
    return {**profile, "committees": committees}


# ── Finance ────────────────────────────────────────────────────────────────────

FINANCE_SQL = """
select
    cycle, total_receipts, total_disbursements, cash_on_hand,
    individual_itemized_contributions, individual_unitemized_contributions,
    pac_contributions, party_contributions, candidate_self_funding,
    pac_pct_of_total, individual_pct_of_total
from fct_member_finance
where member_key = %(key)s
order by cycle desc
"""


@app.get("/members/{member_key}/finance")
def member_finance(member_key: str) -> dict:
    rows = db.query(PROFILE_SQL, {"key": member_key})
    if not rows:
        raise HTTPException(status_code=404, detail="member not found")
    cycles = db.query(FINANCE_SQL, {"key": member_key})
    return {"member_key": member_key, "cycles": cycles}


# ── Legislative record ─────────────────────────────────────────────────────────

SPONSORED_BILLS_SQL = """
select
    b.bill_key, b.identifier, b.title, b.abstract, b.url,
    s.is_primary, s.introduced_date
from fct_bill_sponsorships s
join dim_bills b on b.bill_key = s.bill_key
where s.person_key = %(key)s
order by s.introduced_date desc nulls last
limit %(limit)s
"""

VOTES_SQL = """
select
    b.bill_key, b.identifier, b.title,
    v.vote_event_id, v.vote_date, v.vote_option, v.vote_result, v.motion_text,
    sm.plain_summary, sm.eli5
from fct_votes v
join dim_bills b on b.bill_key = v.bill_key
left join app.bill_summaries sm on sm.bill_key = b.bill_key
where v.person_key = %(key)s
order by v.vote_date desc nulls last
limit %(limit)s
"""


@app.get("/members/{member_key}/record")
def member_record(
    member_key: str,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    rows = db.query(PROFILE_SQL, {"key": member_key})
    if not rows:
        raise HTTPException(status_code=404, detail="member not found")
    params = {"key": member_key, "limit": limit}
    return {
        "member_key": member_key,
        "sponsored": db.query(SPONSORED_BILLS_SQL, params),
        "votes": db.query(VOTES_SQL, params),
    }


# ── Conflict of interest ───────────────────────────────────────────────────────

CONFLICT_SQL = """
select
    coi.cycle, coi.coi_score, coi.risk_level,
    coi.total_receipts, coi.pac_contributions,
    coi.individual_itemized_contributions, coi.individual_unitemized_contributions,
    coi.party_contributions, coi.candidate_self_funding,
    coi.committees_served, coi.regulated_industries,
    coi.evidence_description
from mart_conflict_of_interest coi
where coi.member_key = %(key)s
order by coi.cycle desc
"""


@app.get("/members/{member_key}/conflict")
def member_conflict(member_key: str) -> dict:
    rows = db.query(PROFILE_SQL, {"key": member_key})
    if not rows:
        raise HTTPException(status_code=404, detail="member not found")
    cycles = db.query(CONFLICT_SQL, {"key": member_key})
    latest = cycles[0] if cycles else None
    return {
        "member_key": member_key,
        "latest": latest,
        "history": cycles,
    }


# ── Bill detail + AI summarization ────────────────────────────────────────────

BILL_SQL = """
select
    b.bill_key, b.source_system, b.level, b.state, b.congress, b.session,
    b.bill_type, b.identifier, b.title, b.abstract, b.url,
    b.latest_action_date, b.latest_action_text, b.update_date,
    s.plain_summary, s.eli5, s.model_id, s.generated_at,
    iff(s.bill_key is not null, 'ready', 'none') as summary_status
from dim_bills b
left join app.bill_summaries s on s.bill_key = b.bill_key
where b.bill_key = %(bill_key)s
"""

INSERT_SUMMARY_SQL = """
insert into app.bill_summaries (bill_key, plain_summary, eli5, model_id)
select %(bill_key)s, %(plain_summary)s, %(eli5)s, %(model_id)s
where not exists (
    select 1 from app.bill_summaries where bill_key = %(bill_key)s
)
"""


@app.get("/bills/{bill_key}")
def get_bill(bill_key: str) -> dict:
    rows = db.query(BILL_SQL, {"bill_key": bill_key})
    if not rows:
        raise HTTPException(status_code=404, detail="bill not found")
    return rows[0]


@app.post("/bills/{bill_key}/summarize")
def summarize_bill(bill_key: str) -> dict:
    rows = db.query(BILL_SQL, {"bill_key": bill_key})
    if not rows:
        raise HTTPException(status_code=404, detail="bill not found")
    bill = rows[0]

    if bill["summary_status"] == "ready":
        return {
            "summary_status": "ready",
            "plain_summary": bill["plain_summary"],
            "eli5": bill["eli5"],
        }

    prompt = f"Title: {bill['title'] or bill['identifier']}"
    if bill.get("abstract"):
        prompt += f"\n\nAbstract: {bill['abstract']}"

    msg = _get_claude().messages.create(
        model=SUMMARIZE_MODEL,
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": (
                f"Write two summaries of this legislation:\n\n{prompt}\n\n"
                "1. plain_summary: 2-3 sentences in plain English for a general audience.\n"
                "2. eli5: 1-2 sentences as if explaining to a curious 10-year-old.\n\n"
                'Respond only with JSON: {"plain_summary": "...", "eli5": "..."}'
            ),
        }],
    )

    result = json.loads(msg.content[0].text)
    db.execute(INSERT_SUMMARY_SQL, {
        "bill_key": bill_key,
        "plain_summary": result["plain_summary"],
        "eli5": result["eli5"],
        "model_id": SUMMARIZE_MODEL,
    })

    return {
        "summary_status": "ready",
        "plain_summary": result["plain_summary"],
        "eli5": result["eli5"],
    }


def run() -> None:
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
