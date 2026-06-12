# CivicLens App — Fable Design Prompt

## Overview

I'm building **CivicLens**, an interactive web app that helps voters research candidates, understand campaign finance, and find alignment with their own values. Please help me design the mart models, API endpoints, and frontend structure to power this app.

## Tech Stack

- **Data warehouse:** Snowflake
- **Transformation:** dbt (staging → intermediate → marts)
- **API layer:** FastAPI
- **Frontend:** Streamlit
- **Orchestration:** Prefect
- **AI:** Claude API (used for bill summarization and alignment scoring)

---

## Existing Data Sources (staging models already built)

| Level | Source | What it covers |
|---|---|---|
| Federal | Congress API | Members (House/Senate), committees, bills, votes |
| Federal | FEC API | Candidates, PAC committees, contribution transactions (Schedule A), disbursements (Schedule B) |
| State | OpenStates | Legislators and bills for all 50 states — ingested in daily batches, NY first |
| State | NY Board of Elections | NY state campaign activity (public funds, qualified expenditures) |
| Local | NYC Campaign Finance Board | NYC race contributions (mayor, city council, borough president, etc.) 2017–2025 |
| Demographics | Census ACS 5-year | Congressional district & state populations, income, education, race/ethnicity |

Staging models are clean and standardized in Snowflake. An intermediate model already joins NY legislators to NY BOE campaign finance using fuzzy name matching. No mart models exist yet.

### Bill data specifics

Each bill has:
- `title` — official legislative title
- `abstract` — short summary from OpenStates (may be null for some states)
- `url` — canonical link to the bill on OpenStates
- `plain_summary` — 2–3 sentence plain-English summary (Claude-generated, lazy: created on first app view)
- `eli5` — one-sentence ELI5 version (Claude-generated alongside `plain_summary`)

The app shows `plain_summary` by default, with a toggle to reveal `eli5` and a link to the full bill text. If no summary exists yet, a "Summarize" button triggers generation.

---

## App Features

### 1. Candidate Discovery & Profiles

- Search/filter candidates by office (federal / state / local), state, party, district, election cycle
- Profile view: name, office sought, party, district, background bio
- Link to incumbent legislative record if applicable (bills sponsored, voting history with summaries)

### 2. Platform & Position Tracking

- Stated issue positions where available
- How does their legislative voting record (for incumbents) match their stated platform?
- *(VoteSmart issue ratings are planned but not yet ingested — design this slot to be plugged in)*

### 3. Campaign Finance & Donor Analysis

- Total raised, total spent, cash on hand
- Top donors (individuals and PACs/committees) with contribution amounts
- Donor industry/category breakdown
- Geographic distribution of donors
- Cross-candidate donor analysis: which other candidates are this candidate's donors also funding?
- PAC/committee network: which PACs back this candidate, and who else do those PACs support?

### 4. Value Alignment Scoring

- User inputs their priorities — ranked or rated issues (housing, climate, healthcare, immigration, etc.)
- Score candidates by how well their platform and voting record match the user's priorities
- Surface top-aligned candidates for a given race or geography

### 5. Political Connections & Endorsements

- Who has endorsed this candidate?
- Who notably has NOT endorsed this candidate (key figures in their party or district)?
- Political network: which other politicians or organizations are they connected to (donor overlap, co-sponsorships, committee memberships)?
- *(Endorsement data source TBD — flag what you'd recommend)*

### 6. Likely Outcomes if Elected

- Based on their platform and voting history, what policy changes are they likely to pursue?
- Comparable legislators with similar voting record, donor profile, and party faction — what have they done in office?

### 7. Unified Federal + State + Local Search

- Single search across all three levels
- Consistent profile structure regardless of level (graceful nulls where data doesn't exist)
- Financials displayed at the appropriate level (FEC for federal, NYC CFB for local NYC, NY BOE for state NY)

---

## Design Deliverables

### 1. Mart Model Schema

Define the fact and dimension tables needed to power these features. For each mart model:
- Suggested name and grain
- Key columns
- Source models it builds from
- Which app features it powers

Prioritize what's buildable from existing staging data now vs. what requires new sources.

### 2. Data Gaps

Identify which features require data not yet ingested and recommend the best source for each gap (endorsements, bio data, issue position ratings, etc.).

### 3. FastAPI Endpoint Design

Sketch the key endpoints:
- Candidate search
- Candidate profile
- Finance summary
- Donor network (cross-candidate)
- Alignment score (input: user priorities, output: ranked candidates)
- Bill detail (triggers lazy summary generation if needed)

### 4. Streamlit Page Structure

Propose the navigation and page layout:
- Which pages exist
- What components/widgets are on each page
- How a user flows from discovery → profile → alignment → donor network

### 5. Phased Implementation Plan

Sequence the work so each phase delivers a usable increment:

| Phase | Scope |
|---|---|
| 1 | Candidate directory + basic finance summary (federal + NY) |
| 2 | Bill profiles with summaries + incumbent voting records |
| 3 | Donor network + cross-candidate analysis |
| 4 | Value alignment scoring |
| 5 | Connections, endorsements, likely outcomes |

Please be specific about dbt model names, SQL patterns, and Streamlit component choices where relevant.
