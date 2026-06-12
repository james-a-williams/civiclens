# Source: VoteSmart API

**Phase:** MVP  
**Status:** Active ✅ — re-verified 2026-06-12. Free key registration open at votesmart.org/share/api. A newer OpenAPI/Swagger interface also exists at api.paas.votesmart.io/api — check which the issued key targets before building the connector.  
**Classification:** Foundational

---

## Overview

VoteSmart (votesmart.org) is a nonpartisan nonprofit that maintains the most comprehensive structured database of candidate and officeholder positions in the US. It provides self-reported issue positions (Political Courage Test), interest group ratings, biographical data, and campaign information for federal and state candidates. This is the primary source for "What does this candidate say their position is on Issue X?" — the foundational question for the alignment scorer.

## Access

| Field | Value |
|---|---|
| Official URL | https://votesmart.org/share |
| Documentation | https://api.votesmart.org/docs |
| API Available | Yes |
| Bulk Download | No |
| Scraping Required | No |
| Auth | API key (free, registration at votesmart.org/share) |
| Rate Limit | Not publicly specified; reasonable for pipeline use |
| Cost | Free |

## Coverage

- **Geography:** Federal + all 50 states
- **Update frequency:** Ongoing (as candidates file or update positions)
- **History:** 1990s for some federal candidates; state coverage varies

## Key Data Types

### Political Courage Test (PCT)
Candidates answer structured yes/no/other questions on policy issues. Self-reported. Categories include:

- Abortion / reproductive rights
- Budget / taxes / economy
- Education
- Environment / energy
- Gun control
- Healthcare
- Immigration
- Social issues

This is the closest thing to a structured "candidate position record" available at no cost.

### Interest Group Ratings
Advocacy organizations (NRA, ACLU, AFL-CIO, Chamber of Commerce, Sierra Club, etc.) rate legislators based on voting records. These ratings are an indirect measure of alignment — if a voter trusts a particular org's judgment, that org's rating of a candidate is a useful signal.

### Biographical Data
Education, career history, religion, military service — useful for enriching candidate profiles.

## Key API Endpoints

| Endpoint | Data |
|---|---|
| `Candidate.getByOfficeTypeState` | Candidates by office type and state |
| `Candidate.getByLastname` | Lookup candidate by name |
| `CandidateBio.getAddlBio` | Biographical detail |
| `Rating.getRatingsByCandidate` | All interest group ratings for a candidate |
| `Rating.getSigList` | All special interest groups (for filtering) |
| `Npat.getNpat` | Political Courage Test answers by candidate |

## Primary Key

VoteSmart uses its own `candidateId`. Cross-reference to `bioguide_id` (federal) and `openstates_id` (state) via name + state + district matching — fuzzy join required.

## Data Quality

**Rating: 8/10.** Self-reported positions are genuine signals but not always complete — many candidates decline to fill out the Political Courage Test. Interest group ratings are highly valuable and more complete. Federal coverage is excellent; state coverage is good for contested races, thinner for down-ballot.

## Ingestion Difficulty: 3/10

REST API, XML or JSON responses, free key. Main challenge is entity resolution — VoteSmart IDs don't map directly to Congress.gov bioguide IDs or OpenStates IDs, requiring fuzzy name/state/district matching.

## Why Valuable

**This is the only free structured source for candidate issue positions.** Without it, position data for the alignment scorer must come entirely from the Research Agent (Claude extracting positions from web text), which is powerful but less auditable. VoteSmart provides the structured baseline; the Research Agent fills gaps.

The alignment flow: user takes issue quiz → system scores their positions → compares against VoteSmart PCT answers + interest group ratings + Research Agent-extracted positions → returns ranked candidates.

## Limitations

- Many candidates (especially incumbents who feel "safe") decline to fill out the Political Courage Test
- Interest group ratings reflect organization's scoring rubric, not neutral position measurement
- State-level coverage thinner for non-competitive races
- Entity resolution (VoteSmart ID → bioguide/openstates ID) requires fuzzy matching

## Suggested Connector Structure

```python
# src/connectors/votesmart.py
class VoteSmartConnector(BaseConnector):
    BASE_URL = "https://api.votesmart.org"

    def get_candidate_by_name(self, last_name: str, state: str = None) -> list[dict]: ...
    def get_candidate_bio(self, candidate_id: int) -> dict: ...
    def get_courage_test(self, candidate_id: int) -> dict: ...
    def get_interest_group_ratings(self, candidate_id: int) -> list[dict]: ...
    def get_interest_groups(self, state: str = None) -> list[dict]: ...
```

## Alternative Sources

- Ballotpedia candidate profiles — platform pages exist but require scraping
- OnTheIssues.org — curated positions, scraping required
- Research Agent (Claude) — AI-extracted positions from campaign websites and news; fills gaps VoteSmart misses
