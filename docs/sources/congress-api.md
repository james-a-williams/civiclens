# Source: Congress.gov API

**Phase:** MVP  
**Status:** Active ✅  
**Classification:** Foundational

---

## Overview

The official Library of Congress API for congressional data: members of Congress, legislation, votes, committee memberships, and more. Replaces the deprecated ProPublica Congress API.

## Access

| Field | Value |
|---|---|
| Official URL | https://api.congress.gov |
| Documentation | https://github.com/LibraryOfCongress/api.congress.gov |
| API Available | Yes |
| Bulk Download | No |
| Scraping Required | No |
| Auth | API key (free, via api.data.gov) |
| Rate Limit | 5,000 requests/hour |
| Cost | Free |

## Coverage

- **Geography:** Federal (House + Senate)
- **Update frequency:** Real-time
- **History:** Bills and votes from 1973; members from 1789

## Key Endpoints

| Endpoint | Data |
|---|---|
| `/member` | All current and historical members |
| `/member/{bioguideId}` | Member detail: bio, party, district, terms |
| `/member/{bioguideId}/sponsored-legislation` | Bills sponsored by this member |
| `/bill` | All legislation by congress and type |
| `/bill/{congress}/{type}/{number}/votes` | Roll call votes on a specific bill |
| `/committee` | Committee listings |
| `/committee/{chamber}/{committeeCode}/bills` | Bills referred to a committee |

## Primary Key

`bioguideId` — stable across all congresses (e.g., `W000817` for Elizabeth Warren). Use this as the canonical federal legislator ID.

## Data Quality

**Rating: 9/10.** Official government source. Comprehensive and well-maintained. Responses in JSON or XML.

## Ingestion Difficulty: 2/10

Clean REST API, excellent docs, consistent pagination. Default page size is 20; max 250 per request.

## Why Valuable

Canonical source for "How does this politician vote?" and "What legislation have they sponsored?" Required for the core voting record and legislative activity use cases.

## Limitations

- Federal only — no state legislation
- Vote records are bill-level (roll calls), not committee votes
- Some older records (pre-2000) are incomplete

## Suggested Connector Structure

```python
# src/connectors/congress_api.py
class CongressAPIConnector(BaseConnector):
    BASE_URL = "https://api.congress.gov/v3"

    def get_member(self, bioguide_id: str) -> dict: ...
    def get_members(self, congress: int = None, chamber: str = None) -> list[dict]: ...
    def get_bills(self, congress: int, bill_type: str = "hr") -> list[dict]: ...
    def get_bill_votes(self, congress: int, bill_type: str, bill_number: int) -> dict: ...
    def get_sponsored_legislation(self, bioguide_id: str) -> list[dict]: ...
```

## Alternative Sources

- GovTrack bulk data — clean flat files of all votes and bills, easier for bulk ingestion
- Congress.gov (web) — human-readable version of the same data
