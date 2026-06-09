# Source: FEC API (OpenFEC)

**Phase:** MVP  
**Status:** Active ✅  
**Classification:** Foundational

---

## Overview

The Federal Election Commission's REST API is the primary source for all federal campaign finance data — candidate and committee registrations, individual contributions, PAC disbursements, and independent expenditures.

## Access

| Field | Value |
|---|---|
| Official URL | https://api.open.fec.gov/developers |
| API Available | Yes |
| Bulk Download | Yes (fec.gov/data/browse-data) |
| Scraping Required | No |
| Auth | API key (free, via api.data.gov) |
| Rate Limit | 1,000 requests/hour |
| Cost | Free |

## Coverage

- **Geography:** Federal only (presidential, Senate, House)
- **Update frequency:** Real-time (FEC processes filings continuously)
- **History:** Full electronic filing history from 1994

## Key Endpoints

| Endpoint | Data |
|---|---|
| `/candidates/search` | Search candidates by name, state, office, cycle |
| `/candidate/{id}` | Full candidate record |
| `/schedules/schedule_a` | Individual contributions (receipts) |
| `/schedules/schedule_b` | Disbursements |
| `/committees` | PACs, party committees, candidate committees |
| `/filings` | All official FEC filings |

## Data Quality

**Rating: 9/10.** Official government data. Well-documented. Some gaps in small-donor itemization (contributions under $200 are aggregated). Fuzzy donor name/employer matching required for entity resolution.

## Ingestion Difficulty: 2/10

Clean REST API, good docs, consistent JSON schema. Only challenge is pagination on large datasets (Schedule A has millions of rows).

## Why Valuable

The single authoritative source for who funded every federal candidate. Required for the core "Who funds this politician?" question.

## Limitations

- Federal races only — no state or local
- Individual contributors under $200 not itemized
- Donor entity resolution (same person filing with different name/address) requires fuzzy matching

## Suggested Connector Structure

```python
# src/connectors/fec.py
class FECConnector(BaseConnector):
    BASE_URL = "https://api.open.fec.gov/v1"

    def get_candidate(self, candidate_id: str) -> dict: ...
    def get_contributions(self, candidate_id: str, cycle: int) -> list[dict]: ...
    def get_committee(self, committee_id: str) -> dict: ...
    def get_disbursements(self, committee_id: str) -> list[dict]: ...
```

## Alternative Sources

- OpenSecrets bulk CSV — enriched FEC data with industry/sector classifications added
- FEC bulk downloads — flat files when API rate limits are a concern
