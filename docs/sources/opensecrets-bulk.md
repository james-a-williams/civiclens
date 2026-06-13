# Source: OpenSecrets Bulk Data

**Phase:** Phase 2  
**Status:** Active ✅ — verified 2026-06-12. Note: the OpenSecrets **API was discontinued April 15, 2025**; bulk CSV downloads remain available, free for educational use with account signup (opensecrets.org/bulk-data/signup).  
**Classification:** Nice to have (enrichment layer on top of FEC)

---

## Overview

OpenSecrets (Center for Responsive Politics) enriches raw FEC data with industry and sector classifications, lobbyist mappings, and dark money tracking. The bulk CSV download is free for educational use. Most valuable as an enrichment layer on top of FEC API data — it takes raw FEC filings and adds the "which industry is this donor from?" layer that FEC doesn't provide.

## Access

| Field | Value |
|---|---|
| Official URL | https://www.opensecrets.org/bulk-data |
| Documentation | https://www.opensecrets.org/open-data/bulk-data-documentation |
| API Available | No (API is paid subscription only) |
| Bulk Download | Yes (CSV, free with account approval) |
| Scraping Required | No |
| Auth | Free account + approval (academic/nonprofit/journalism) |
| Rate Limit | N/A (bulk download) |
| Cost | Free (with approval for educational use) |

## Coverage

- **Geography:** Federal (same as FEC)
- **Update frequency:** Annual (election cycle data released post-election)
- **History:** Full history from 1990 (some data from 1980s)

## Key Data Tables

| Table | Description |
|---|---|
| `candidates` | Candidate master list with party, state, district |
| `committees` | PAC and committee records |
| `pac_to_candidate` | PAC contributions to candidates (with industry codes) |
| `pac_to_pac` | PAC-to-PAC transfers |
| `individual_contributions` | Itemized individual donations with employer/industry |
| `lobbying` | Lobbying disclosure reports with client and issue codes |
| `industry_codes` | Lookup table for OpenSecrets industry/sector taxonomy |

## Industry/Sector Taxonomy

OpenSecrets assigns every donor to one of ~80 industries and 13 sectors. This is the key enrichment:

```
Sector: Finance/Insurance/Real Estate
  Industry: Commercial Banks
  Industry: Securities & Investment
  Industry: Insurance
  ...
```

Joining FEC contributions to this taxonomy answers "Which industries fund this politician?"

## Data Quality

**Rating: 9/10.** Manually curated, extremely high quality. The industry classification is the best available for federal campaign finance analysis. Slight lag (data released annually after election cycle closes).

## Ingestion Difficulty: 4/10

Flat CSV files, well-documented schema. Main challenge is joining OpenSecrets entity IDs to FEC IDs (they don't share a primary key system).

## Why Valuable

Without OpenSecrets, you can see raw donation amounts from FEC but can't classify by industry. OpenSecrets adds the critical "oil companies gave this candidate $X" layer that makes the data meaningful.

## Limitations

- Requires account approval (educational use case)
- Federal only — use FollowTheMoney for state-level industry breakdowns
- Annual release cadence; mid-cycle data not available in bulk form
- API (real-time) is paid subscription only

## Suggested Connector Structure

```python
# src/connectors/opensecrets_bulk.py
class OpenSecretsBulkConnector(BaseConnector):
    DATA_DIR = "data/raw/opensecrets"

    def download_cycle_data(self, cycle: int) -> None: ...
    def load_pac_to_candidate(self, cycle: int) -> pd.DataFrame: ...
    def load_individual_contributions(self, cycle: int) -> pd.DataFrame: ...
    def load_industry_codes(self) -> pd.DataFrame: ...
    def enrich_with_industry(self, fec_df: pd.DataFrame) -> pd.DataFrame: ...
```

## Alternative Sources

- FEC API — raw data without industry enrichment
- FollowTheMoney — state-level with industry codes; similar classification system
