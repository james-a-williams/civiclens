# Source: GDELT Project

**Phase:** Phase 2  
**Status:** Active ✅  
**Classification:** Nice to have (replaces NewsAPI)

---

## Overview

The Global Database of Events, Language, and Tone (GDELT) monitors broadcast, print, and web news across nearly every country in 100+ languages, updating every 15 minutes. 100% free, public domain, no rate limits on bulk access. Replaces NewsAPI for the CivicLens news monitoring use case.

## Access

| Field | Value |
|---|---|
| Official URL | https://www.gdeltproject.org |
| Documentation | https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ |
| API Available | Yes (GDELT DOC 2.0 API for full-text search) |
| Bulk Download | Yes (15-minute CSV chunks, public GCS bucket) |
| Scraping Required | No |
| Auth | None — fully open |
| Rate Limit | None on bulk downloads; DOC API has soft limits |
| Cost | Free, public domain |

## Coverage

- **Geography:** Global (U.S. coverage excellent)
- **Update frequency:** Every 15 minutes (bulk files); real-time (DOC API)
- **History:** GDELT 2.0 from 2015; GDELT 1.0 from 1979

## Access Methods

### 1. Bulk CSV Downloads (Recommended for pipeline)
15-minute CSV chunks dropped to a public Google Cloud Storage bucket. Each chunk contains all news articles processed in that window with metadata, themes, tone scores, and entity mentions.

```
# Master file list:
http://data.gdeltproject.org/gdeltv2/lastupdate.txt
```

### 2. GDELT DOC 2.0 API (Recommended for ad-hoc)
Full-text search API for finding articles about specific people, topics, or themes:
```
https://api.gdeltproject.org/api/v2/doc/doc?query=politician_name&mode=artlist&format=json
```

### 3. Google BigQuery (Recommended for large-scale analysis)
Full 2.0 archive queryable via BigQuery. Best for historical analysis.

## Key Fields

| Field | Description |
|---|---|
| `url` | Article URL |
| `title` | Article headline |
| `seendate` | Timestamp |
| `tone` | Sentiment score (-100 to +100) |
| `persons` | Named persons mentioned |
| `organizations` | Named orgs mentioned |
| `themes` | GDELT theme codes (e.g., `TAX_FNCACT_POLITICIAN`) |
| `sourcecountry` | Source country |

## Data Quality

**Rating: 8/10.** Massive coverage but noisy — some low-quality sources, some misclassified sentiment. Excellent for trend analysis and article volume. Tone scores are useful but not as accurate as purpose-built sentiment models.

## Ingestion Difficulty: 4/10

Bulk files are straightforward CSV. DOC API is simple JSON. Main challenge is volume (each 15-min file is large) and filtering relevant articles about specific politicians.

## Why Valuable

Public domain, no rate limits, global coverage, entity extraction built in. Perfect replacement for NewsAPI. Enables "What is the media saying about this politician?" use case without any subscription cost.

## Limitations

- Volume is large — needs filtering strategy to keep Snowflake costs manageable
- Tone/sentiment scores are coarse; consider running TextBlob/VADER on full text for better accuracy
- Entity extraction (persons field) can be noisy — "Trump" might match many different Trumps
- Coverage of local news is less complete than national

## Suggested Connector Structure

```python
# src/connectors/gdelt.py
class GDELTConnector(BaseConnector):
    MASTER_LIST_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
    DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

    def get_latest_files(self) -> list[str]: ...
    def download_bulk_file(self, url: str) -> pd.DataFrame: ...
    def search_articles(self, query: str, mode: str = "artlist") -> list[dict]: ...
    def get_articles_for_person(self, name: str, days_back: int = 7) -> list[dict]: ...
```

## Alternative Sources

- MediaCloud — free academic API, curated sources, better quality control
- CommonCrawl — raw web crawl data; requires significant processing
- NewsAPI — avoid: non-commercial restriction on free tier, 100 req/day cap
