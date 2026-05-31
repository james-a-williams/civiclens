# CivicLens

> A full-stack data pipeline that pulls civic data, transforms it into analytics-ready models, and surfaces insights in an interactive dashboard. Active development — portfolio project.

---

## What is CivicLens

CivicLens ingests civic data (legislation, voting records, public filings) from public APIs and datasets, transforms it through a structured dbt pipeline, and exposes it via a FastAPI + Streamlit stack. Claude Code agents are embedded throughout the pipeline to automate research, planning, and monitoring tasks.

---

## Architecture

```
Raw Sources
│
▼
src/connectors/       ← Python connectors pull from civic APIs and public datasets
│
▼
Snowflake             ← Raw and staging layers in the data warehouse
│
▼
dbt Fusion            ← Transformation layer (staging → intermediate → marts)
│
▼
FastAPI               ← API layer serves mart data and agent outputs
│
▼
Streamlit             ← Frontend dashboard for exploration and visualization
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Ingestion | Python connectors |
| Warehouse | Snowflake |
| Transformation | dbt Fusion |
| Orchestration | Prefect |
| API | FastAPI |
| Dashboard | Streamlit |
| Agents | Claude API (Claude Code) |

---

## Repo Structure

```
src/connectors/       — data source connectors (one file per source)
src/dbt/              — transformation models (staging → intermediate → marts)
src/agents/           — Claude Code agentic workflows (research, planning, monitor)
src/orchestration/    — Prefect flows and schedules
docs/                 — plans, source research, and agent alert outputs
```

---

## Getting Started

The stack is still being built — these steps will expand as components come online.

1. Clone the repo
2. Copy `.env.example` → `.env` and fill in credentials
3. Add Snowflake credentials to `profiles.yml` (gitignored)
4. `pip install -r requirements.txt` *(coming soon)*

---

## Status / Roadmap

- [x] Repo scaffold and architecture defined
- [ ] Snowflake environment setup
- [ ] First connector (source TBD)
- [ ] dbt staging models
- [ ] FastAPI layer
- [ ] Streamlit dashboard
- [ ] Agent workflows wired to pipeline
