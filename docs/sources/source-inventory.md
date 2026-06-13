# CivicLens — Civic Data Source Inventory

_Generated: 2026-06-02. All sources verified active._

---

## Deprecated Sources (Removed from Stack)

| Source | Reason |
|---|---|
| Google Civic Information API | Deprecated March 31, 2025 — API shut down |
| ProPublica Congress API | Deprecated — no new API keys, historical reference only |
| X (Twitter) API | Free tier: 1 req/15 min — unusable for a pipeline |
| NewsAPI | Free tier: non-commercial restriction, 100 req/day cap |
| FollowTheMoney API | Merged into OpenSecrets — site unmaintained, data frozen at 2024 cycle, no updates (removed 2026-06-12) |
| LegiScan | Superseded by OpenStates (more open, no restrictive tier) |

---

## Verified Source Stack

### Phase 1 — MVP

_Minimum set to answer: How closely do I align with this candidate? Who represents me? How do politicians vote vs. what they claim?_

| # | Source | URL | API | Bulk Download | Scraping | Coverage | Update Freq | Cost | Quality | Difficulty | Phase |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Congress.gov API | api.congress.gov | Yes | No | No | Federal | Real-time | Free | 9/10 | 2/10 | MVP |
| 2 | OpenStates API v3 | v3.openstates.org | Yes | No | No | All 50 states | Weekly | Free (500 req/day) | 8/10 | 3/10 | MVP |
| 3 | VoteSmart API | votesmart.org/share | Yes | No | No | Federal + all states | Ongoing | Free | 8/10 | 3/10 | MVP |
| 4 | Census Bureau API | api.census.gov | Yes | Yes | No | National → block group | Annual (ACS) | Free | 9/10 | 3/10 | MVP |

### Phase 2 — Extended Coverage

| # | Source | URL | API | Bulk Download | Scraping | Coverage | Update Freq | Cost | Quality | Difficulty | Phase |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | FEC API | api.open.fec.gov | Yes | Yes | No | Federal | Real-time | Free | 9/10 | 2/10 | Phase 2 |
| 7 | OpenSecrets Bulk Data | opensecrets.org/bulk-data | No | Yes (CSV) | No | Federal | Annual | Free (approval req'd) | 9/10 | 4/10 | Phase 2 |
| 8 | GDELT | gdeltproject.org | Yes (DOC API) | Yes | No | Global news | 15-min chunks | Free | 8/10 | 4/10 | Phase 2 |
| 9 | GovTrack | govtrack.us/data | No | Yes | No | Federal | Daily | Free | 8/10 | 3/10 | Phase 2 |

### Phase 3 — Advanced

| # | Source | URL | API | Bulk | Scraping | Coverage | Update Freq | Cost | Quality | Difficulty | Phase |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 | Ballotpedia | ballotpedia.org | Partial | No | Yes* | National | Ongoing | Free* | 8/10 | 7/10 | Phase 3 |
| 11 | OpenFEC Bulk | fec.gov/data/browse-data | No | Yes | No | Federal | Quarterly | Free | 9/10 | 5/10 | Phase 3 |
| 12 | LobbyView | lobbyview.org | Yes | Yes | No | Federal lobbying | Annual | Free (academic) | 8/10 | 4/10 | Phase 3 |

_*Ballotpedia scraping: ToS allows non-commercial use. Verify before production use._

---

## Top 20 Highest-Value Sources (Ranked)

_Ranked by value to the core alignment use case: "How closely do my views match this candidate?"_

1. **Congress.gov API** — Voting records and sponsored legislation for every federal member. The "how they actually voted" foundation.
2. **OpenStates API** — Same as above for all 50 state legislatures. Open source, free.
3. **VoteSmart API** — Only free structured source for candidate self-reported issue positions + interest group ratings. Core input to the alignment scorer.
4. **Census Bureau API** — District demographics. Context for who candidates represent.
5. **Research Agent (Claude API)** — Fills VoteSmart gaps by extracting positions from campaign sites, speeches, and news. Already in Week 9 plan.
6. **FEC API** — Gold standard for federal campaign finance. "Who funds this candidate?" context layer.
7. ~~FollowTheMoney API~~ — Deprecated 2026-06: merged into OpenSecrets, data frozen at 2024. State finance now requires per-state portals.
8. **OpenSecrets Bulk CSV** — Enriched FEC data with industry/sector classifications. Adds "which industries fund this candidate?" layer.
9. **GDELT** — Unlimited free news monitoring. Public domain. Queryable via BigQuery or 15-min CSV drops.
10. **GovTrack** — Voting statistics (party loyalty, missed votes, issue area breakdown). Useful for nuanced voting record analysis.
11. LobbyView — Federal lobbying disclosures with entity resolution. Academic license, free.
12. Ballotpedia — Most complete ballot measure and candidate platform coverage. Scraping required.
13. OpenFEC Bulk — Full FEC data in flat files when API rate limits are a constraint.
14. PACER — Federal court records. Pay-per-page; use only for targeted lookups.
15. BallotReady — Structured ballot data for local races. Paid, but best local coverage.
16. ProPublica Nonprofit Explorer — 990 filings for PACs and issue orgs. Free API still active.
17. USA Spending API — Federal contracts and grants. Free, official.
18. Data.gov — Cross-agency data portal. Good for finding agency-specific datasets.
19. Geocodio — Geocoding + district appending. Cheap per-call. Useful for "who represents this address?"
20. OECD / World Bank — International comparison data. Nice-to-have for context.

---

## Primary Key Strategy

| Entity | Recommended Key | Source |
|---|---|---|
| Politicians / Members | `bioguide_id` (federal) or `openstates_id` (state) | Congress.gov, OpenStates |
| Candidates | `fec_candidate_id` (e.g. `P00009423`) | FEC API |
| Committees / PACs | `fec_committee_id` (e.g. `C00575795`) | FEC API |
| Donors (individuals) | FEC contributor name + zip + employer (fuzzy) | FEC bulk |
| Corporations | FEC committee ID or EIN | FEC + OpenSecrets |
| Government entities | FIPS code (counties/states) or OCD division ID | Census, OpenStates |
| Districts | OCD division ID (e.g. `ocd-division/country:us/state:ca/cd:12`) | OpenStates |

---

## Proposed Data Architecture

```
Raw Sources (APIs + Bulk)
│
▼
RAW schema (Snowflake)
│  Congress API responses, OpenStates JSON, VoteSmart positions,
│  Census ACS tables, FEC filings, FollowTheMoney records, GDELT CSV
│
▼
STAGING schema (dbt)
│  stg_members, stg_votes, stg_bills, stg_positions,
│  stg_ratings, stg_demographics, stg_finance, stg_news
│
▼
INTERMEDIATE schema (dbt)
│  Identity resolution (bioguide ↔ fec_id ↔ openstates_id)
│  Entity enrichment, deduplication, geography joins
│
▼
MART schema (dbt)
│  mart_candidates, mart_candidate_positions, mart_voting_records,
│  mart_alignment_scores, mart_district_context, mart_finance_summary
│
▼
FastAPI → Streamlit
  Serves mart data; AI/RAG layer over enriched profiles
```

---

## Where No National Dataset Exists

| Data Type | Gap | Recommendation |
|---|---|---|
| State campaign finance | Each state has its own system; no national aggregator with current data (FollowTheMoney frozen at 2024 post-merger) | Per-state portals, added as states are prioritized (NY BOE already ingested) |
| Local/municipal elections | No central source | BallotReady (paid) or Ballotpedia scraping |
| School board / special districts | Fragmented by jurisdiction | Scrape + manual collection per district |
| Lobbying (state-level) | 50 separate state systems | NCSL has links; NationalLobbyistIndex covers some |
| Judicial elections | No comprehensive source | Ballotpedia per-state; state court websites |
