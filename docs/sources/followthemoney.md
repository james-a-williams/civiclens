# Source: FollowTheMoney API

**Phase:** MVP  
**Status:** Active ✅  
**Classification:** Foundational

---

## Overview

FollowTheMoney.org (National Institute on Money in State Politics) is the leading aggregator of state-level campaign finance data across all 50 states. Fills the critical gap left by FEC, which only covers federal races.

## Access

| Field | Value |
|---|---|
| Official URL | https://www.followthemoney.org/our-data/apis |
| Documentation | https://www.followthemoney.org/our-data/apis/documentation |
| API Available | Yes |
| Bulk Download | No |
| Scraping Required | No |
| Auth | API key (free, register at followthemoney.org) |
| Rate Limit | Not publicly specified; contact for high-volume use |
| Cost | Free |

## Coverage

- **Geography:** All 50 states (state legislative and gubernatorial races)
- **Update frequency:** Ongoing (as state filings are processed)
- **History:** 2000+ for most states; some states back to 1990s

## Key API Functions

| Endpoint | Data |
|---|---|
| `candidate` | Candidate lookup by name, state, office, year |
| `contributor` | Contributor lookup (donors to state candidates) |
| `contributions` | Contributions to a specific candidate or from a specific contributor |
| `pac` | PAC information and contributions |
| `industry` | Industry-coded contributions (similar to OpenSecrets sectors) |

## Data Quality

**Rating: 8/10.** Best available for state campaign finance. Standardized across states. Data quality depends on state filing quality, which varies. Industry codes are manually assigned and very valuable.

## Ingestion Difficulty: 3/10

REST API, free, well-documented. Response format is XML by default; JSON available. Key must be appended as query param.

## Why Valuable

Without this source, there's no programmatic way to answer "Who funds the governor?" or "Which industries donate to state legislators?" for any of the 50 states. FEC covers federal only; this covers the rest.

## Limitations

- Relies on state filings — quality varies by state's disclosure laws
- Some states have weak disclosure requirements (dark money gaps)
- Not real-time; processing lag varies by state

## Suggested Connector Structure

```python
# src/connectors/followthemoney.py
class FollowTheMoneyConnector(BaseConnector):
    BASE_URL = "https://api.followthemoney.org"

    def get_candidate(self, name: str, state: str, year: int = None) -> list[dict]: ...
    def get_contributions(self, candidate_id: str) -> list[dict]: ...
    def get_industry_totals(self, candidate_id: str) -> list[dict]: ...
    def get_pac_contributions(self, state: str, year: int) -> list[dict]: ...
```

## Alternative Sources

- Individual state ethics/finance commission APIs — authoritative but 50 separate integrations
- OpenSecrets — federal only; industry classifications are richer but no state coverage
