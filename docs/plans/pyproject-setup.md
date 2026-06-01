# Plan: Scaffold pyproject.toml

**Branch:** `feat/pyproject-setup`
**Week:** 1 (final deliverable)

## Goal

Add `pyproject.toml` to the repo root to formalize Python project metadata, dependency declarations, and tooling configuration.

## Steps

1. **Project metadata** — name, version, description, Python `>=3.12` constraint
2. **Core dependencies** — packages needed now or imminently:
   - `requests` — HTTP calls in connectors
   - `pyarrow` — Parquet read/write
   - `python-dotenv` — `.env` loading
   - `tenacity` — retry logic (Week 4 hardening, declare early)
   - `pandas` — DataFrame work (Week 3)
   - `snowflake-connector-python` — Snowflake connection (Week 5)
3. **Dev dependencies** — `pytest`, `ruff`
4. **Ruff config** — line length 100, enable `E`, `F`, `I` (isort) rules
5. **Pytest config** — testpaths = `["tests"]`

## Files

| File | Action |
|------|--------|
| `pyproject.toml` | Create at repo root |

## Acceptance Criteria

- `pyproject.toml` exists and is valid TOML
- `python -m pytest` resolves test path correctly
- Ruff can be invoked with `ruff check .`
