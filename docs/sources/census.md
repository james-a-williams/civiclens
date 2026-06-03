# Source: Census Bureau API

**Phase:** MVP  
**Status:** Active ✅  
**Classification:** Foundational

---

## Overview

The U.S. Census Bureau API provides demographic, economic, and geographic data at every level of geography — from national down to block group. Primary use case in CivicLens is district-level demographic context (population, income, race/ethnicity, education) for understanding who politicians represent.

## Access

| Field | Value |
|---|---|
| Official URL | https://api.census.gov/data.html |
| Documentation | https://www.census.gov/data/developers.html |
| API Available | Yes |
| Bulk Download | Yes |
| Scraping Required | No |
| Auth | API key required (free, via census.gov/developers) |
| Rate Limit | 500 requests/day without key; unlimited with key |
| Cost | Free |

## Coverage

- **Geography:** National → state → county → tract → block group
- **Update frequency:** Annual (ACS 5-year is most comprehensive; released ~December each year)
- **History:** ACS 5-year available from 2009

## Key Datasets

| Dataset | Description | API Path |
|---|---|---|
| ACS 5-Year | American Community Survey 5-year estimates; most detailed | `/data/2024/acs/acs5` |
| ACS 1-Year | More recent but smaller samples; metro areas only | `/data/2024/acs/acs1` |
| Decennial Census | Population counts every 10 years | `/data/2020/dec/pl` |

## High-Value Variables for CivicLens

| Variable | Description |
|---|---|
| `B01003_001E` | Total population |
| `B19013_001E` | Median household income |
| `B02001_002E` | White alone population |
| `B02001_003E` | Black or African American alone |
| `B03001_003E` | Hispanic or Latino |
| `B15003_022E` | Bachelor's degree holders (25+) |
| `B27001_001E` | Health insurance coverage |

## Geographic Identifiers

- **FIPS codes** — standard for state (2-digit) + county (5-digit) + tract (11-digit)
- **Congressional district** — available in ACS via `congressional district` geography level
- Cross-reference FIPS codes with OCD division IDs from OpenStates for district joins

## Data Quality

**Rating: 9/10.** Official government data. Margin of error included. ACS 5-year is the most reliable; ACS 1-year has higher sampling error for small geographies.

## Ingestion Difficulty: 3/10

REST API with non-standard query format (`?get=VAR1,VAR2&for=congressional+district:*&in=state:06`). Use the `census` Python package to simplify queries.

## Why Valuable

Provides demographic context for every legislative district — essential for understanding whether politicians' votes and donors align with their constituents.

## Limitations

- ACS estimates have margin of error (especially for small areas)
- Data is 1–5 years old by the time it's released
- Tract/block-group level requires understanding of geographic hierarchy

## Suggested Connector Structure

```python
# src/connectors/census.py
class CensusConnector(BaseConnector):
    BASE_URL = "https://api.census.gov/data"

    def get_district_demographics(self, state_fips: str, congress: int = None) -> list[dict]: ...
    def get_county_demographics(self, state_fips: str) -> list[dict]: ...
    def get_variables(self, dataset: str, year: int) -> list[dict]: ...
```

## Alternative Sources

- Census bulk downloads — full flat files when you need many geographies
- IPUMS — harmonized Census microdata for longitudinal analysis
