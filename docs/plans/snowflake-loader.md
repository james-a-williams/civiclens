# Plan: Snowflake Raw Layer Loader

## Context

Connectors for Congress, FEC, OpenStates, and Census all return data as `list[dict]` via `fetch_all()`, but currently only write to local parquet files. The dbt staging layer is already defined and expects 9 raw tables in `CIVICLENS_RAW.PUBLIC`. A `SnowflakeClient` (`src/connectors/snowflake_client.py`) exists with `get_raw_connection()` but isn't yet used. This work closes that gap by adding a loader that fetches from each connector and writes to Snowflake.

---

## Approach

Create a single new file: `src/connectors/snowflake_loader.py`.

It will contain three functions:

### `load_table(conn, records, table_name)`
- Converts `list[dict]` → `pd.DataFrame`
- Adds a `load_date` column (UTC date string, `YYYY-MM-DD`)
- Calls `write_pandas(conn, df, table_name, auto_create_table=True, overwrite=True)`
- Skips gracefully if `records` is empty (logs and returns)
- Full-refresh strategy (overwrite=True) is correct for now — these are small civic datasets with no incremental key yet

### `load_connector_data(conn, tables)`
- Accepts `dict[str, list[dict]]` (the shape returned by every `fetch_all()`)
- Calls `load_table()` for each key/value pair

### `load_all()`
- Opens one `get_raw_connection()` connection (reused across all loads)
- Instantiates and calls `fetch_all()` on each connector:
  - `CongressAPIConnector` — reads `CONGRESS_API_KEY` from env
  - `FECConnector` — reads `FEC_API_KEY`
  - `OpenStatesConnector` — reads `OPENSTATES_API_KEY`
  - `CensusConnector` — reads `CENSUS_API_KEY`
- Passes each result to `load_connector_data()`
- Closes connection in a `finally` block
- Logs start/finish for each connector (connector name + table row counts)

**No changes needed** to `BaseConnector`, `SnowflakeClient`, or any existing connector. The loader is purely additive.

---

## Key Implementation Notes

- **`write_pandas`** from `snowflake.connector.pandas_tools` — available via `snowflake-connector-python>=3.10` (declared in `pyproject.toml`). Handles DDL and INSERT in one call.
- **Column casing**: `write_pandas` uppercases column names in Snowflake by default. This is fine — Snowflake resolves unquoted identifiers case-insensitively, so dbt `source()` queries work without quoting.
- **`load_date`**: Added as `datetime.date.today().isoformat()` string before DataFrame construction. Staging models cast it via `load_date::date`.
- **`get_raw_connection()`** targets `CIVICLENS_RAW.PUBLIC` by default (from env vars `SNOWFLAKE_RAW_DATABASE` / `SNOWFLAKE_RAW_SCHEMA`).

---

## Files

| Action | Path |
|--------|------|
| Create | `src/connectors/snowflake_loader.py` |
| Create | `tests/connectors/test_snowflake_loader.py` |

---

## Tests

Use `unittest.mock.patch` (not `responses`) since there are no HTTP calls.

- `test_load_table_adds_load_date` — mock `write_pandas`, assert `load_date` column present in the DataFrame passed to it
- `test_load_table_skips_empty_records` — pass `[]`, assert `write_pandas` is NOT called
- `test_load_table_correct_table_name` — assert table_name arg passed to `write_pandas` matches input
- `test_load_connector_data_calls_load_table_for_each_key` — pass 2-key dict, assert `load_table` called twice
- `test_load_all_calls_each_connector` — mock all 4 `fetch_all()` + `get_raw_connection`, assert each connector runs once

---

## Verification

1. `pytest tests/connectors/test_snowflake_loader.py -v` — all tests pass
2. With real credentials: `python -c "from src.connectors.snowflake_loader import load_all; load_all()"` — confirm tables appear in `CIVICLENS_RAW.PUBLIC` via `SHOW TABLES`
3. `dbt run --select staging` from `src/dbt/` — all 10 staging views build without errors
4. `dbt test --select staging` — primary key tests pass for all 9 source tables