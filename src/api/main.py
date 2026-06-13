"""CivicLens API — serves mart data to the Streamlit frontend.

Phase 1 endpoints: candidate search, candidate profile, finance summary.
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Query

from . import db

app = FastAPI(title="CivicLens API", version="0.1.0")

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


def run() -> None:
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)
