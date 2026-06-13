"""CivicLens API — serves mart data to the Streamlit frontend.

Phase 1: candidate search, profile, finance summary.
Phase 2: bill detail, bill summarization (Claude Haiku), candidate record.
"""

import json
import logging

import anthropic
import uvicorn
from fastapi import FastAPI, HTTPException, Query

from . import db

logger = logging.getLogger(__name__)

app = FastAPI(title="CivicLens API", version="0.1.0")

SUMMARIZE_MODEL = "claude-haiku-4-5-20251001"

_claude: anthropic.Anthropic | None = None


def _get_claude() -> anthropic.Anthropic:
    global _claude
    if _claude is None:
        _claude = anthropic.Anthropic()
    return _claude

SEARCH_SQL = """
select
    candidacy_key, display_name, party, level, office, state, district,
    cycle, is_incumbent, source_system,
    count(*) over () as total_count
from dim_candidates
where (%(q)s is null or display_name ilike '%%' || %(q)s || '%%')
  and (%(level)s is null or level = %(level)s)
  and (%(state)s is null or state = %(state)s)
  and (%(party)s is null or party ilike '%%' || %(party)s || '%%')
  and (%(district)s is null or district = %(district)s)
  and (%(cycle)s is null or cycle = %(cycle)s)
  and (%(office)s is null or office ilike '%%' || %(office)s || '%%')
order by display_name
limit %(limit)s offset %(offset)s
"""

PROFILE_SQL = """
select candidacy_key, person_key, display_name, party, level, office, state,
       district, cycle, incumbent_challenge, is_incumbent, source_system, source_id
from dim_candidates
where candidacy_key = %(key)s
"""

OTHER_CANDIDACIES_SQL = """
select candidacy_key, office, state, district, cycle, source_system
from dim_candidates
where person_key = %(person_key)s and candidacy_key != %(key)s
order by cycle desc
"""

DISTRICT_SQL = """
select district_key, geo_level, name, total_population, median_household_income,
       pct_white, pct_black, pct_hispanic, pct_bachelors, pct_insured
from dim_districts
where (%(geo_level)s = 'congressional_district'
       and geo_level = 'congressional_district'
       and state = %(state)s and district_number = %(district)s)
   or (%(geo_level)s = 'state' and geo_level = 'state' and state = %(state)s)
"""

FINANCE_SQL = """
select coverage, total_raised, total_spent, cash_on_hand, public_funds_received,
       matchable_amount_total, contribution_count, unique_donor_count,
       avg_contribution, pct_small_dollar
from fct_candidate_finance
where candidacy_key = %(key)s
"""

TOP_DONORS_SQL = """
select max(contributor_name) as contributor_name, max(employer_name) as employer_name,
       max(city) as city, max(state) as state,
       sum(amount) as total_amount, count(*) as contribution_count
from fct_contributions
where candidacy_key = %(key)s and contributor_name is not null
group by donor_key
order by total_amount desc
limit %(limit)s
"""

TOP_EMPLOYERS_SQL = """
select employer_name, sum(amount) as total_amount, count(*) as contribution_count
from fct_contributions
where candidacy_key = %(key)s and employer_name is not null and employer_name != ''
group by employer_name
order by total_amount desc
limit %(limit)s
"""

GEO_BREAKDOWN_SQL = """
select city, state, sum(amount) as total_amount, count(*) as contribution_count
from fct_contributions
where candidacy_key = %(key)s and city is not null
group by city, state
order by total_amount desc
limit %(limit)s
"""


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/candidates")
def search_candidates(
    q: str | None = None,
    level: str | None = Query(None, pattern="^(federal|state|local)$"),
    state: str | None = None,
    party: str | None = None,
    district: int | None = None,
    cycle: int | None = None,
    office: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    rows = db.query(
        SEARCH_SQL,
        {
            "q": q,
            "level": level,
            "state": state.upper() if state else None,
            "party": party,
            "district": district,
            "cycle": cycle,
            "office": office,
            "limit": limit,
            "offset": offset,
        },
    )
    total = rows[0]["total_count"] if rows else 0
    for row in rows:
        row.pop("total_count", None)
    return {"results": rows, "total": total, "limit": limit, "offset": offset}


@app.get("/candidates/{candidacy_key}")
def candidate_profile(candidacy_key: str) -> dict:
    rows = db.query(PROFILE_SQL, {"key": candidacy_key})
    if not rows:
        raise HTTPException(status_code=404, detail="candidacy not found")
    profile = rows[0]

    other = db.query(
        OTHER_CANDIDACIES_SQL,
        {"person_key": profile["person_key"], "key": candidacy_key},
    )

    # District context: House races get their congressional district,
    # everything else gets state-level demographics.
    district = None
    if profile["state"]:
        is_house = profile["level"] == "federal" and profile["district"] is not None
        geo = db.query(
            DISTRICT_SQL,
            {
                "geo_level": "congressional_district" if is_house else "state",
                "state": profile["state"],
                "district": profile["district"],
            },
        )
        district = geo[0] if geo else None

    return {**profile, "other_candidacies": other, "district_context": district}


@app.get("/candidates/{candidacy_key}/finance")
def candidate_finance(candidacy_key: str, top_n: int = Query(10, ge=1, le=50)) -> dict:
    rows = db.query(FINANCE_SQL, {"key": candidacy_key})
    if not rows:
        # Valid candidacy with no finance rows is a legitimate state
        # (e.g. candidate who never filed); distinguish from a bad key.
        exists = db.query(PROFILE_SQL, {"key": candidacy_key})
        if not exists:
            raise HTTPException(status_code=404, detail="candidacy not found")
        return {"summary": None, "top_donors": [], "top_employers": [], "geo_breakdown": []}

    summary = rows[0]
    # Donor detail only exists where we have transaction-grain data.
    has_transactions = summary["coverage"] == "nyc_cfb"
    params = {"key": candidacy_key, "limit": top_n}
    return {
        "summary": summary,
        "top_donors": db.query(TOP_DONORS_SQL, params) if has_transactions else [],
        "top_employers": db.query(TOP_EMPLOYERS_SQL, params) if has_transactions else [],
        "geo_breakdown": db.query(GEO_BREAKDOWN_SQL, params) if has_transactions else [],
    }


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

SPONSORED_BILLS_SQL = """
select
    b.bill_key, b.identifier, b.title, b.abstract, b.url,
    s.is_primary, s.introduced_date
from fct_bill_sponsorships s
join dim_bills b on b.bill_key = s.bill_key
where s.person_key = (
    select person_key from dim_candidates where candidacy_key = %(candidacy_key)s
)
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
where v.person_key = (
    select person_key from dim_candidates where candidacy_key = %(candidacy_key)s
)
order by v.vote_date desc nulls last
limit %(limit)s
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


@app.get("/candidates/{candidacy_key}/record")
def candidate_record(
    candidacy_key: str,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    params = {"candidacy_key": candidacy_key, "limit": limit}
    sponsored = db.query(SPONSORED_BILLS_SQL, params)
    votes = db.query(VOTES_SQL, params)
    if not sponsored and not votes:
        exists = db.query(PROFILE_SQL, {"key": candidacy_key})
        if not exists:
            raise HTTPException(status_code=404, detail="candidacy not found")
    return {"sponsored": sponsored, "votes": votes}


def run() -> None:
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
