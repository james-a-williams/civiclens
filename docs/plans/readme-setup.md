# Plan: Setup README

## Goal

Create a top-level `README.md` that gives portfolio visitors and collaborators a clear picture of what CivicLens is, what it's building toward, and how to get started locally.

## Sections

### 1. Header
- Project name + one-line description
- Status badge: active development / portfolio project

### 2. What is CivicLens
- 2–3 sentences: pulls civic data (legislation, voting records, public filings), transforms it into analytics-ready models, surfaces insights in an interactive dashboard
- Note that Claude Code agents are embedded throughout the pipeline

### 3. Architecture
- Reuse the pipeline diagram from CLAUDE.md:
  ```
  Raw Sources → connectors → Snowflake → dbt → FastAPI → Streamlit
  ```
- One sentence per layer explaining its role

### 4. Tech Stack
Quick reference table:

| Layer | Tool |
|---|---|
| Ingestion | Python connectors |
| Warehouse | Snowflake |
| Transformation | dbt Fusion |
| Orchestration | Prefect |
| API | FastAPI |
| Dashboard | Streamlit |
| Agents | Claude API (Claude Code) |

### 5. Repo Structure
4–5 key directories only — no exhaustive listing:
- `src/connectors/` — data source connectors
- `src/dbt/` — transformation models (staging → intermediate → marts)
- `src/agents/` — Claude Code agentic workflows
- `src/orchestration/` — Prefect flows
- `docs/` — plans, source research, agent alert outputs

### 6. Getting Started
Minimal since the stack is still being built — honest placeholder:
1. Clone the repo
2. Copy `.env.example` → `.env` and fill in credentials
3. Add Snowflake credentials to `profiles.yml` (gitignored)
4. `pip install -r requirements.txt` *(coming soon)*

### 7. Status / Roadmap
Honest about early stage — shows intentionality:
- [x] Repo scaffold and architecture defined
- [ ] Snowflake environment setup
- [ ] First connector (source TBD)
- [ ] dbt staging models
- [ ] FastAPI layer
- [ ] Streamlit dashboard
- [ ] Agent workflows wired to pipeline

## Notes
- Keep tone direct — this is a portfolio project, not a product
- No fake screenshots or placeholder data visualizations
- Revisit getting started section once first connector and dbt models exist
