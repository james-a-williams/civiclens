# Plan: Complete Phase 1 Ingestion Sources + Connector Tests

**Branch:** `feat/ingestion-sources-1-2` (in progress)
**Goal:** Ship all four MVP data source connectors with a passing test suite before moving to Phase 2.

---

## Status

| # | Source | Connector | Tests | Notes |
|---|---|---|---|---|
| 1 | Congress.gov API | ✅ `congress_api.py` | ❌ | Done |
| 2 | OpenStates API v3 | ❌ | ❌ | Next |
| 3 | VoteSmart API | ❌ | ❌ | Next |
| 4 | Census Bureau API | ❌ | ❌ | Next |
| — | FEC API | ✅ `fec.py` | ❌ | Phase 2 source, already built |
| — | Base connector | ✅ `base.py` | ❌ | Done |

---

## Tasks

### 1. OpenStates connector (`src/connectors/openstates.py`)
- Auth: API key via `OPENSTATES_API_KEY` env var
- Endpoints to cover:
  - `/people` — legislators by jurisdiction
  - `/bills` — bill search by state + session
  - `/votes` — votes on bills
- Pagination: cursor-based (`pagination.next_page` in response)
- Rate limit: 500 req/day on free tier — respect with `rate_limit_calls` in base
- Output shape: raw JSON per endpoint, one record per response item

### 2. VoteSmart connector (`src/connectors/votesmart.py`)
- Auth: API key via `VOTESMART_API_KEY` env var
- Endpoints to cover:
  - `Officials.getByOfficeState` — elected officials by state
  - `Rating.getCandidateRating` — interest group ratings per candidate
  - `Votes.getBillsByStateRecent` — recent bills
- Note: XML-first API — parse to dict before returning
- Rate limit: not documented; be conservative (1 req/sec default)

### 3. Census Bureau connector (`src/connectors/census.py`)
- Auth: API key via `CENSUS_API_KEY` env var
- Datasets to cover:
  - ACS 5-year (`acs/acs5`) — demographic fields by congressional district
  - Decennial (`dec/dhc`) — population by geography
- Key fields: total population, age, race/ethnicity, median income, educational attainment
- Geography: national, state, congressional district (`cd`)
- No pagination — all results returned in a single response per query

### 4. Tests for all connectors (`tests/connectors/`)
- Use `pytest` + `respx` (async HTTP mocking) or `responses` for sync
- One test file per connector: `test_base.py`, `test_congress_api.py`, `test_fec.py`, `test_openstates.py`, `test_votesmart.py`, `test_census.py`
- Cover per connector:
  - Happy path: valid response returns parsed records
  - Auth error: 401/403 raises a clear exception
  - Rate limit: 429 triggers retry/backoff logic in base
  - Empty result: endpoint returns zero records without crashing
- Do NOT hit live APIs in tests — mock all HTTP

---

## Sequence

```
1. Write OpenStates connector
2. Write VoteSmart connector
3. Write Census connector
4. Add tests/ directory + pytest config
5. Write tests for base + existing connectors (Congress, FEC)
6. Write tests for new connectors (OpenStates, VoteSmart, Census)
7. Wire up CI (if not already passing)
8. PR + merge
```

---

## After This PR

Phase 2 sources (FollowTheMoney, OpenSecrets bulk, GDELT, GovTrack) and the dbt staging layer come next. See `docs/sources/source-inventory.md` for the full stack.
