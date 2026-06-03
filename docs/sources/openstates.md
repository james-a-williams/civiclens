# Source: OpenStates API v3

**Phase:** MVP  
**Status:** Active ✅  
**Classification:** Foundational

---

## Overview

Open States is an open-source project that aggregates state legislative data across all 50 states. Provides legislators, bills, votes, committee memberships, and district boundaries for state government. The state-level equivalent of Congress.gov API.

## Access

| Field | Value |
|---|---|
| Official URL | https://v3.openstates.org |
| Documentation | https://docs.openstates.org/api-v3/ |
| API Available | Yes |
| Bulk Download | No (API only) |
| Scraping Required | No |
| Auth | API key (free, register at openstates.org) |
| Rate Limit | ~500 requests/day (free tier; limits in flux) |
| Cost | Free |

## Coverage

- **Geography:** All 50 US states + DC + PR
- **Update frequency:** Weekly (state legislature schedule dependent)
- **History:** Varies by state; most have 3–5 years

## Key Endpoints

| Endpoint | Data |
|---|---|
| `/people` | State legislators (current + historical) |
| `/people/{id}` | Legislator detail: bio, party, district, roles |
| `/bills` | Bills by state, session, subject |
| `/bills/{id}` | Bill detail: sponsors, votes, actions, text |
| `/bills/{id}/votes` | Roll call votes on a specific bill |
| `/jurisdictions` | List of all covered jurisdictions |

## Primary Key

`openstates_id` — stable unique ID per person (e.g., `ocd-person/...`). Also surfaces `bioguide_id` where available for federal cross-referencing.

## Data Quality

**Rating: 8/10.** Open-source, community-maintained. Quality varies by state — larger states (CA, NY, TX) are excellent; smaller states can lag. Bills from some states missing full text.

## Ingestion Difficulty: 3/10

Well-documented API with consistent JSON. Rate limit on free tier requires careful pagination strategy. Consider caching aggressively.

## Why Valuable

The only practical free source for "Who are my state legislators?" and "How do state politicians vote?" Fills the massive gap left by Google Civic Info's deprecation.

## Limitations

- Rate limits on free tier require caching
- Some states have incomplete bill text
- Update cadence depends on when state legislatures are in session
- Historical data depth varies by state

## Suggested Connector Structure

```python
# src/connectors/openstates.py
class OpenStatesConnector(BaseConnector):
    BASE_URL = "https://v3.openstates.org"

    def get_people(self, state: str, current: bool = True) -> list[dict]: ...
    def get_person(self, openstates_id: str) -> dict: ...
    def get_bills(self, state: str, session: str = None, subject: str = None) -> list[dict]: ...
    def get_bill_votes(self, bill_id: str) -> list[dict]: ...
```

## Alternative Sources

- LegiScan — similar coverage, 400 req/day free tier; less open than OpenStates
- State legislature websites directly — authoritative but require per-state scrapers
