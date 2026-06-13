# CivicLens App — Mart, API, and Frontend Design

_Response to `civiclens-app-fable-prompt.md`. Grounded in the staging layer as it exists at commit `4b97a0e` (2026-06-12)._

---

## Reality Check: What's Actually Staged Today

The prompt describes a few things as already built that aren't yet. The design below works around these, but they shape phasing, so they're called out first:

| Prompt assumption | Reality |
|---|---|
| FEC Schedule A contributions + Schedule B disbursements staged | Only `stg_fec__candidates` (directory) and `stg_fec__committees` (directory) exist. No transactions, no financial totals. |
| Congress API bills + votes staged | Only `stg_congress__members` and House/Senate committee directories exist. |
| Bills have `abstract` and `url` | `stg_openstates__bills` selects only `bill_id, identifier, title, state, session, created_at, updated_at`. Abstract, URL, sponsorships, and votes sit unparsed in the raw VARIANT — a staging change, not a new ingestion. |
| `plain_summary` / `eli5` on bills | Don't exist anywhere yet. Designed below as an app-writable table, not a dbt model (dbt shouldn't own rows written at request time). |
| NY BOE = "campaign activity" | It's one row per candidate per election year (public funds + qualified expenditures). Aggregate only — no donors, so no "top donors" for NY state races from this source. |

The one transaction-grain finance source that exists today is **NYC CFB contributions** (with contributor name, employer, occupation, city/state/zip, amount). That makes NYC local races the proving ground for donor analysis, with federal following once FEC Schedule A is ingested.

---

## 1. Mart Model Schema

### Identity resolution (intermediate layer, prerequisite for everything)

The hard problem is that the same person appears under different IDs: `bioguide_id` (Congress), `fec_candidate_id` (FEC), `openstates_id` (OpenStates), `filer_id` (NY BOE), `recipient_id` (NYC CFB). The existing `int_legislators__ny_boe_activity` already does this for one pair (Jaro-Winkler ≥ 85 on last name + district match). Generalize it:

**`int_persons__id_crosswalk`** — grain: one row per resolved person.

| Column | Notes |
|---|---|
| `person_key` | Surrogate: `coalesce(bioguide_id, openstates_id, fec_candidate_id, ...)` hashed — stable as long as the highest-priority source ID is present |
| `bioguide_id`, `fec_candidate_id`, `openstates_id`, `ny_boe_filer_id`, `nyc_cfb_recipient_id` | Nullable source IDs |
| `canonical_name`, `match_method`, `match_confidence` | Keep match provenance auditable, same spirit as the agent logging rule |

Matching pattern (same as the existing intermediate model): exact match on state + district + office level first, then `jarowinkler_similarity(upper(last_name), ...) >= 85` as fallback. FEC→Congress is easier than it looks: FEC candidate IDs encode office (`H`/`S`/`P` prefix) and `stg_fec__candidates` carries state + district, and `incumbent_challenge = 'I'` flags the rows that must have a `bioguide_id` match — use that as a match-quality test.

### Dimensions

**`dim_candidates`** — grain: one row per person per office sought per cycle (a *candidacy*, not a person — one person can run for two offices across cycles).

| Column | Source |
|---|---|
| `candidacy_key` (PK), `person_key` (FK) | crosswalk |
| `display_name`, `party`, `level` (`federal`/`state`/`local`) | unified across sources |
| `office`, `state`, `district`, `cycle` | `stg_fec__candidates`, `stg_ny_boe__activity`, `stg_nyc_cfb__contributions` (distinct recipient × cycle × office_code) |
| `incumbent_challenge`, `is_current_legislator` | FEC + presence in members/people |
| `bio` | **null for now — data gap #2** |

Sources: all three candidate-bearing staging models + crosswalk. Powers: features 1, 7.

**`dim_legislators`** — grain: one row per sitting legislator (federal + state). Columns: `person_key`, `name`, `chamber`, `party`, `state`, `district`, `level`. Sources: `stg_congress__members` ∪ `stg_openstates__people` (flatten `current_role` VARIANT for chamber/district). Powers: features 1, 2, 6.

**`dim_bills`** — grain: one row per bill. Columns: `bill_id`, `identifier`, `title`, `abstract`, `url`, `state`, `session`, `level`, `status`. Sources: re-staged `stg_openstates__bills` (pull `abstract`/`openstates_url` out of the raw VARIANT) ∪ future `stg_congress__bills`. **Summaries are deliberately not columns here** — see "Bill summaries" below. Powers: features 2, 6.

**`dim_committees`** — grain: one row per FEC committee. Mostly a pass-through of `stg_fec__committees` + `designation`/`committee_type` decoded to readable labels. Powers: features 3, 5.

**`dim_districts`** — grain: one row per geography (congressional district ∪ state). Columns: `district_key` (state_fips + district_number, or state_fips alone), `total_population`, `median_household_income`, race/ethnicity/education/insurance columns, plus derived `pct_*` rates. Sources: both census staging models. Powers: profile context, feature 4 geography filter.

### Facts

**`fct_contributions`** — grain: one row per contribution transaction, unified across sources with a `source_system` column (`nyc_cfb` now, `fec_sa` later, `followthemoney` later).

| Column | Notes |
|---|---|
| `contribution_key` | source + transaction_ref |
| `candidacy_key`, `person_key` | via crosswalk on recipient |
| `donor_key` | `md5(upper(trim(contributor_name)) \|\| coalesce(zip,'') \|\| upper(coalesce(employer_name,'')))` — the FEC-standard fuzzy donor identity; imperfect but consistent |
| `contributor_name`, `contributor_type`, `employer_name`, `occupation`, `city`, `state`, `zip` | from staging |
| `amount`, `matchable_amount`, `contribution_date`, `cycle` | |

Materialize incremental on `load_at` (matches the existing raw-layer `load_at` convention). Powers: feature 3 entirely.

**`fct_candidate_finance`** — grain: one row per candidacy per cycle. Columns: `total_raised`, `total_spent`, `cash_on_hand`, `contribution_count`, `unique_donor_count`, `avg_contribution`, `public_funds_received`, `pct_small_dollar` (< $200). Sources: aggregate of `fct_contributions` (NYC), `stg_ny_boe__activity` (NY state — only `public_funds_received` and `qualified_campaign_expenditures` populate; the rest null), FEC `/candidate/{id}/totals` once ingested (federal — this endpoint gives raised/spent/cash-on-hand directly without needing Schedule A). Graceful nulls per level are a feature, not a bug — the API surfaces which fields each level supports. Powers: features 3, 7.

**`fct_donor_candidate_edges`** — grain: one row per `donor_key` × `candidacy_key`. Columns: `total_amount`, `contribution_count`, `first_date`, `last_date`. This is `fct_contributions` rolled up one level, and it's the table that makes cross-candidate donor analysis a self-join instead of a scan:

```sql
-- "who else do this candidate's donors fund?"
select b.candidacy_key, count(distinct a.donor_key) as shared_donors,
       sum(b.total_amount) as shared_donor_dollars
from fct_donor_candidate_edges a
join fct_donor_candidate_edges b
  on a.donor_key = b.donor_key and a.candidacy_key != b.candidacy_key
where a.candidacy_key = :candidate
group by 1 order by 2 desc
```

Powers: features 3, 5.

**`fct_bill_sponsorships`** — grain: one row per legislator × bill. Columns: `person_key`, `bill_id`, `sponsorship_type` (primary/cosponsor), `classification`. Source: `lateral flatten` over the `sponsorships` VARIANT in raw OpenStates bills (new staging model `stg_openstates__bill_sponsorships`), ∪ Congress bill sponsors later. Powers: features 2, 5, 6.

**`fct_votes`** — grain: one row per legislator × roll call. Columns: `person_key`, `bill_id`, `vote_event_id`, `option` (yes/no/abstain), `date`. Source: OpenStates `votes` VARIANT (same flatten pattern) + Congress.gov roll calls (new ingestion). Powers: features 2, 4, 6.

**`fct_candidate_issue_signals`** — grain: one row per candidacy × issue (housing, climate, healthcare, immigration, etc. — a seed file `seeds/issue_taxonomy.csv` defines the list). Columns: `issue`, `signal_score` (−1..1), `evidence_count`, `signal_sources` (votes / sponsorships / stated positions). Built from: bills tagged with issues (Claude batch-tags bill titles+abstracts; tags stored in an agent-output table, joined in) × `fct_votes` + `fct_bill_sponsorships`, plus VoteSmart positions when ingested (this is the prompt's "design the slot" — VoteSmart lands as one more `signal_source` row feeding the same grain). **This is the precompute that makes alignment scoring cheap**: user priorities never touch a mart; the API computes a weighted dot product over this table at request time. Powers: features 2, 4, 6.

### Bill summaries (`plain_summary` / `eli5`)

Request-time Claude output doesn't belong in a dbt model — dbt would clobber it on every run. Instead: a Snowflake table `app.bill_summaries` (`bill_id` PK, `plain_summary`, `eli5`, `model_id`, `generated_at`) owned and written by FastAPI. The API left-joins it onto `dim_bills` at read time. dbt treats it as a source if any mart ever needs it (e.g. a "summarized coverage" metric).

### Buildable now vs. blocked

| Model | Buildable from existing staging? |
|---|---|
| `int_persons__id_crosswalk`, `dim_candidates`, `dim_legislators`, `dim_committees`, `dim_districts` | **Yes, now** |
| `fct_contributions`, `fct_donor_candidate_edges` | **Yes, now** — NYC CFB only; schema designed for FEC/FollowTheMoney union later |
| `fct_candidate_finance` | Partial now (NYC aggregate + NY BOE); federal needs FEC totals ingestion |
| `dim_bills`, `fct_bill_sponsorships` | Staging change only (flatten existing raw VARIANT) — no new ingestion |
| `fct_votes` | OpenStates portion: staging change. Federal: new Congress.gov ingestion |
| `fct_candidate_issue_signals` | Needs bills+votes marts first, plus Claude issue tagging |

---

## 2. Data Gaps

Ordered by how much app surface each unblocks. Source recommendations align with `docs/sources/source-inventory.md`.

| Gap | Blocks | Recommended source | Effort |
|---|---|---|---|
| **FEC financial totals** | Federal finance summary (Phase 1) | FEC API `/candidate/{id}/totals` — totals without transaction volume. Extend `src/connectors/fec.py` | Small |
| **FEC Schedule A (+ B)** | Federal donor analysis (Phase 3) | FEC API `/schedules/schedule_a` for top-N per candidate; OpenFEC bulk CSVs if full coverage needed (API pagination on millions of rows is painful) | Medium |
| **Bill abstract/url/sponsors/votes** | Bill profiles (Phase 2) | Already in raw OpenStates VARIANT — staging-only change | Small |
| **Federal bills + votes** | Incumbent voting records (Phase 2) | Congress.gov API `/bill` + House roll-call endpoints (beta since May 2025, 2023–present, existing key works). **Senate has no Congress.gov endpoint** — ingest senate.gov public roll-call XML (no key) | Medium |
| **Issue positions / ratings** | Alignment scoring (Phase 4) | VoteSmart API (already researched in `docs/sources/votesmart.md`); research agent fills gaps from campaign sites | Medium |
| **Donor industry classification** | Industry breakdown (Phase 3) | Now: Claude batch-classifies NYC CFB `employer_name`/`occupation` strings into a seed taxonomy (cheap, demos the agentic angle). Later: OpenSecrets bulk CSVs for FEC-standard industry codes (free educational signup; note their API was discontinued April 2025 — bulk only) | Small now / Medium later |
| **Candidate bios** | Profile page | Federal: bioguide. Broader: Wikipedia/Wikidata API (structured, free). Ballotpedia scraping as last resort (ToS: non-commercial only) | Small–Medium |
| **Endorsements** | Feature 5 | **No good free structured source exists.** Recommendation: research-agent pattern — Claude searches news/press releases per candidate, extracts endorsements **with citation URLs** into a reviewed table. Honest framing for a portfolio: "agent-curated, human-spot-checked." Ballotpedia has some coverage but scraping is brittle. "Who *hasn't* endorsed" is only computable as: party figures in the same geography minus recorded endorsers — frame it as "no endorsement found," never as a negative fact | Large |
| **State finance beyond NY** | Feature 7 at scale | **No national aggregator with current data exists** — FollowTheMoney merged into OpenSecrets and stopped updating (frozen at 2024; removed from the stack). Per-state finance portals, added one at a time as states are prioritized — same pattern as the NY BOE connector | Medium per state, deferred |

---

## 3. FastAPI Endpoint Design

All read endpoints query marts directly (Snowflake via `snowflake_client.py`); no ORM needed. Pydantic response models give graceful nulls for free.

```
GET  /candidates                      # search/filter
     ?q= &level= &state= &party= &district= &cycle= &office=
     → paginated [{candidacy_key, name, party, office, state, district, level, cycle}]
     Backed by: dim_candidates. ILIKE on name is fine at this scale.

GET  /candidates/{candidacy_key}      # profile
     → identity + offices held + bio + district demographics
     Backed by: dim_candidates ⋈ dim_legislators ⋈ dim_districts

GET  /candidates/{candidacy_key}/finance
     → {totals: {...nullable by level...}, top_donors: [...],
        industry_breakdown: [...], geo_breakdown: [...],
        coverage: "fec" | "ny_boe" | "nyc_cfb"}   # tells the UI what to render
     Backed by: fct_candidate_finance + fct_donor_candidate_edges + fct_contributions

GET  /candidates/{candidacy_key}/donor-network
     ?min_shared_donors=3
     → {nodes: [candidates, pacs], edges: [{from, to, shared_donors, shared_dollars}]}
     Backed by: fct_donor_candidate_edges self-join (SQL above)

GET  /candidates/{candidacy_key}/record
     → {sponsored: [...bills...], votes: [...with bill title + summary if cached...]}
     Backed by: fct_bill_sponsorships, fct_votes ⋈ dim_bills

POST /alignment/score
     body: {priorities: {"housing": 5, "climate": 3, ...},
            geography: {state, district?}, level?}
     → ranked [{candidacy_key, name, score, per_issue: {...}, evidence_counts}]
     Backed by: fct_candidate_issue_signals — weighted dot product in SQL,
     normalized by evidence_count so a candidate with 2 votes doesn't outrank
     one with 200. Stateless: user priorities are never persisted server-side.

GET  /bills/{bill_id}
     → {identifier, title, abstract, url, plain_summary?, eli5?, summary_status}
     Left-joins app.bill_summaries; summary_status: "ready" | "none"

POST /bills/{bill_id}/summarize        # the lazy-generation trigger
     → 202 {summary_status: "pending"} then idempotent
     Claude call (claude-haiku-4-5 — cheap, summaries don't need frontier reasoning),
     writes plain_summary + eli5 + model_id to app.bill_summaries in one call.
     Idempotency: INSERT ... WHERE NOT EXISTS; concurrent requests are harmless.

GET  /search?q=                        # unified federal+state+local
     → grouped {candidates: [...], legislators: [...], bills: [...]}
```

Lazy-summary flow: the frontend GETs the bill, sees `summary_status: "none"`, renders the "Summarize" button, POSTs, polls the GET once or twice. Keeping generation behind an explicit POST (not a side effect of GET) keeps GETs fast and cacheable and makes Claude spend user-intentional.

---

## 4. Streamlit Page Structure

Multi-page app via `st.navigation`/`st.Page` (the modern API, not the `pages/` directory convention).

**🔍 Find Candidates** (home)
- `st.text_input` search + sidebar filters (`st.selectbox` level/state/cycle, `st.multiselect` party) → `GET /candidates`
- Results as `st.dataframe(selection_mode="single-row")` — click navigates to profile via `st.session_state`

**👤 Candidate Profile** (the hub — most user time lands here)
- Header: name, party badge, office, incumbent flag
- `st.tabs(["Overview", "Finance", "Record", "Connections"])`
  - *Overview*: bio, district demographics as `st.metric` row, issue-signal radar chart (plotly `Scatterpolar`)
  - *Finance*: `st.metric` row (raised / spent / cash on hand — render only fields the `coverage` flag supports), top donors `st.dataframe`, industry `plotly` treemap, donor-geography choropleth (`plotly` zip-level)
  - *Record*: sponsored bills + votes table; each row expands (`st.expander`) showing `plain_summary`, `st.toggle("ELI5")`, link to full text, and the Summarize `st.button` when missing
  - *Connections*: donor-network graph (`st-link-analysis` component; fallback: plotly scatter + edge traces), shared-donor table, endorsements list with citation links (Phase 5)

**🧭 Match Me**
- `st.select_slider` (0–5) per issue from the taxonomy, geography picker → `POST /alignment/score`
- Ranked result cards: score `st.progress` bar, per-issue breakdown in `st.expander`, button → profile
- Methodology note in an expander — for a civic app, showing the scoring math is a trust feature

**📜 Bill Explorer**
- Search + state/session filters → bill list → detail pane with the same summary/ELI5/Summarize component as the Record tab (factor it into a shared `components/bill_card.py`)

**🕸 Donor Network** (Phase 3)
- Standalone explorer: pick a candidate or PAC, interactive graph, depth-1 expansion on node click

User flow: **Find Candidates** → click → **Profile/Overview** → Finance tab ("who funds them?") → Connections ("who else do those donors fund?") → **Match Me** ("which of these candidates fits *me*?") — each profile links back into Match Me with geography pre-filled.

---

## 5. Phased Implementation Plan

Each phase ships a usable increment; PR-per-step per the repo workflow.

**Phase 1 — Candidate directory + finance summary (federal + NY + NYC)**
1. `data/persons-id-crosswalk` — `int_persons__id_crosswalk` + tests (incumbent-must-match check)
2. `data/candidate-dims` — `dim_candidates`, `dim_legislators`, `dim_districts`, `dim_committees`
3. `data/fec-candidate-totals` — extend `src/connectors/fec.py` with `/candidate/{id}/totals`; `stg_fec__candidate_totals`
4. `data/finance-summary-mart` — `fct_contributions` (NYC CFB), `fct_candidate_finance`
5. `feat/api-candidates` — FastAPI app scaffold, `/candidates`, `/candidates/{key}`, `/finance`
6. `feat/streamlit-shell` — navigation, Find Candidates, Profile (Overview + Finance tabs)

**Phase 2 — Bill profiles + voting records**
1. `data/openstates-bill-detail` — re-stage bills with abstract/url; `stg_openstates__bill_sponsorships`, `stg_openstates__bill_votes` (lateral flatten)
2. `data/congress-bills-votes` — extend `congress_api.py`; federal staging
3. `data/bills-marts` — `dim_bills`, `fct_bill_sponsorships`, `fct_votes`
4. `feat/bill-summaries` — `app.bill_summaries` table, `GET /bills/{id}`, `POST /bills/{id}/summarize`
5. `feat/streamlit-bills` — Bill Explorer + Record tab, shared bill-card component

**Phase 3 — Donor network**
1. `data/fec-schedule-a` — Schedule A ingestion (top-N per federal candidate via API first; bulk later if needed)
2. `data/donor-edges` — donor_key resolution, `fct_donor_candidate_edges`, extend `fct_contributions` union
3. `agent/donor-industry-tagging` — Claude classification of employer/occupation → industry seed taxonomy
4. `feat/donor-network` — `/donor-network` endpoint, Connections tab, Donor Network page

**Phase 4 — Value alignment**
1. `agent/bill-issue-tagging` — batch-tag bills against `seeds/issue_taxonomy.csv`
2. `data/issue-signals-mart` — `fct_candidate_issue_signals`
3. `data/votesmart` — VoteSmart connector + staging, joined as an additional signal source
4. `feat/alignment` — `POST /alignment/score`, Match Me page

**Phase 5 — Connections, endorsements, likely outcomes**
1. `agent/endorsement-research` — research-agent extraction with citations into a reviewed table
2. `data/legislator-similarity` — comparable-legislators: cosine similarity over (vote vectors + issue signals + donor industry mix); top-5 per legislator as a mart
3. `feat/connections` — endorsements UI, "similar legislators — what they did in office" panel (Claude-generated from the similar legislators' records, cached like bill summaries)

---

## Open Questions

1. **Crosswalk grain for NYC CFB**: `recipient_id` is per-committee, and candidates can have multiple committees across cycles — verify against the raw data before locking `dim_candidates` grain.
2. **OpenStates 500 req/day cap** vs. backfilling sponsorship/vote detail for all NY sessions — may need the bulk data dumps instead of the API for the backfill.
3. **Alignment score methodology** deserves a short ADR in `docs/` before Phase 4 — it's the most opinionated (and most scrutinizable) thing a civic app can ship.
