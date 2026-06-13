# CivicLens — CLAUDE.md

## Project Overview

CivicLens is a full-stack data pipeline portfolio project built to demonstrate end-to-end data engineering skills — from raw ingestion to a live dashboard — targeting fullstack data engineering roles at startups.

The project pulls civic data (legislation, voting records, public filings, etc.), transforms it into analytics-ready models, exposes it via an API, and surfaces insights in an interactive frontend. Claude Code agents are embedded throughout the pipeline for research, planning, and monitoring tasks.

**Status:** Active development. This is a public portfolio repo — code quality, architecture decisions, and agentic workflows are all part of what's on display.

---

## Architecture

```
Raw Sources
│
▼
src/connectors/          ← Python connectors pull from civic APIs / public datasets
│
▼
Snowflake                ← Raw + staging layers in the data warehouse
│
▼
dbt Fusion               ← Transformation layer (staging → intermediate → mart models)
│
▼
FastAPI                  ← API layer serves mart data and agent outputs
│
▼
Streamlit                ← Frontend dashboard for exploration and visualization
```

Claude Code agents run across multiple layers:

- **Research agent** (`src/agents/research.py`) — explores data sources, summarizes schema, drafts connector specs
- **Planning agent** (`src/agents/planning.py`) — breaks down features into tasks, proposes dbt model structure
- **Monitor agent** (`src/agents/monitor.py`) — watches pipeline runs, surfaces anomalies, posts Prefect alerts

Orchestration is handled by **Prefect**, which schedules connector runs, dbt builds, and agent checks.

---

## Repo Structure

```
civiclens/
├── src/
│   ├── connectors/      # Python data source connectors (one file per source)
│   ├── transforms/      # Standalone Python transformation logic (pre-dbt or utility)
│   ├── agents/          # Claude Code agentic workflows (research, planning, monitor)
│   ├── api/             # FastAPI layer serving mart data (run: civiclens-api)
│   ├── app/             # Streamlit frontend (run: streamlit run src/app/app.py)
│   ├── dbt/             # dbt Fusion project
│   │   ├── models/
│   │   │   ├── staging/
│   │   │   ├── intermediate/
│   │   │   └── marts/
│   │   ├── tests/
│   │   ├── macros/
│   │   ├── seeds/
│   │   ├── snapshots/
│   │   ├── analyses/
│   │   └── dbt_project.yml
│   └── orchestration/   # Prefect flows and schedules
├── tests/               # pytest test suite (unit + integration)
├── docs/                # Architecture diagrams, ADRs, and reference docs
├── .github/workflows/   # GitHub Actions CI/CD pipelines
├── .claude/commands/    # Custom Claude Code slash commands
├── .env.example         # Template for required environment variables
├── .gitignore
└── CLAUDE.md            # This file
```

---

## Development Workflow

- **Branching:** Every change lives on a feature branch. Branch naming: `type/short-description-kebab-case` (see `/branch` command below).
- **PRs:** Every change merges via PR — no direct commits to `main`.
- **CI/CD:** GitHub Actions runs on every PR: linting, type checks, and tests must pass before merge.
- **Commits:** Present-tense imperative style (`add connector for FEC filings`, `fix dbt ref in mart model`). One logical change per commit.
- **Environments:** `.env` for local secrets (never committed). Snowflake credentials go in `profiles.yml` (gitignored). Copy `.env.example` to `.env` to get started.

Branch prefixes:

| Prefix    | Use for                                      |
|-----------|----------------------------------------------|
| `feat/`   | New features or capabilities                 |
| `fix/`    | Bug fixes                                    |
| `docs/`   | Documentation, diagrams, ADRs                |
| `data/`   | New data sources, connectors, dbt models     |
| `agent/`  | Claude Code agent workflows and prompts      |

---

## Claude Code Agent Instructions

Agents in `src/agents/` are Python scripts that use the Claude API to perform scoped, autonomous tasks within the pipeline.

### General rules for all agents

- Agents output structured results (JSON or Markdown) to a defined location — never print-and-forget.
- No agent takes destructive or irreversible actions (dropping tables, deleting files, pushing to remotes) without explicit user confirmation.
- Agents log their reasoning steps alongside outputs so they're auditable.
- Keep agent scope narrow: one agent, one job. Don't chain side effects.

### Research agent (`src/agents/research.py`)

- Purpose: Explore a new data source, summarize its schema, and draft a connector spec.
- Input: A data source name or URL.
- Output: A Markdown doc in `docs/sources/` describing fields, update cadence, auth method, and a suggested connector structure.

### Planning agent (`src/agents/planning.py`)

- Purpose: Take a feature description and decompose it into a sequenced task list with file-level implementation notes.
- Input: A natural language feature description.
- Output: A Markdown plan saved to `docs/plans/` and optionally opened in the editor.

### Monitor agent (`src/agents/monitor.py`)

- Purpose: Watch Prefect flow run logs, detect anomalies (late runs, schema drift, null spikes), and surface a summary.
- Input: A time window and optional flow name filter.
- Output: A structured alert summary posted to a configured Slack webhook or written to `docs/alerts/`.

---

## Custom Commands

Custom slash commands live in `.claude/commands/`. They are invoked as `/command-name` inside Claude Code.

### `/branch`

Suggests a well-formatted branch name for the current task, then creates it.

**Usage:** Type `/branch` — Claude will ask what the branch is for (if not already clear), suggest 2–3 options in `type/short-description-kebab-case` format, and confirm before running `git checkout -b`.

See implementation: `.claude/commands/branch.md`
