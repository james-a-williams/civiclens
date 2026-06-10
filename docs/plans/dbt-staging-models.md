# Plan: dbt Staging Models

## Context
The ingestion layer is complete — 4 connectors (FEC, Congress API, OpenStates, Census) write raw data to `CIVICLENS_RAW.PUBLIC` in Snowflake. The dbt project structure exists (`src/dbt/`) with correct materializations configured but zero models. This plan builds the staging layer only.

**Staging layer contract:** 1:1 with raw source tables. Each model selects from exactly one raw table. Allowed operations: column renames, type casts, null PK filtering. No joins, no unions, no JSON flattening, no computed/surrogate keys — those belong in intermediate.

> Note: The Snowflake loader (Parquet → Snowflake) is not yet implemented, so `dbt run` won't succeed until that lands. `dbt compile` can be verified immediately.

---

## Files to Create

### 1. `src/dbt/models/staging/_sources.yml`
Defines one source named `raw` pointing at `CIVICLENS_RAW.PUBLIC` with all 9 raw tables:

| Table Name | Connector |
|---|---|
| `candidates` | FEC |
| `committees` | FEC |
| `members` | Congress API |
| `house_committees` | Congress API |
| `senate_committees` | Congress API |
| `people` | OpenStates |
| `bills` | OpenStates |
| `congressional_districts` | Census |
| `states` | Census |

---

### 2. Staging SQL Models (9 files in `src/dbt/models/staging/`)

One model per raw table. Pattern: `select <renames + casts> from {{ source('raw', '<table>') }} where <pk> is not null`

**`stg_fec__candidates.sql`**
FEC fields are already snake_case — just cast types.
`candidate_id` (PK), `name`, `office`, `office_full`, `state`, `district`, `party`, `party_full`, `election_year::int`, `incumbent_challenge`, `has_raised_funds::boolean`, `load_date::date`

**`stg_fec__committees.sql`**
`committee_id` (PK), `name`, `committee_type`, `committee_type_full`, `designation`, `state`, `party`, `cycle::int`, `organization_type`, `filing_frequency`

**`stg_congress__members.sql`**
Congress.gov returns camelCase — rename with double-quotes (Snowflake case-sensitive).
`"bioguideId" as bioguide_id` (PK), `name as member_name`, `"partyName" as party`, `state`, `district`, `"updateDate"::date as updated_at`
Leave `terms` (nested array) untouched — flattening happens in intermediate.

**`stg_congress__house_committees.sql`**
`"systemCode" as committee_code` (PK), `"name" as committee_name`, `"url" as url`

**`stg_congress__senate_committees.sql`**
Same column set as house_committees:
`"systemCode" as committee_code` (PK), `"name" as committee_name`, `"url" as url`

**`stg_openstates__people.sql`**
`id as openstates_id` (PK), `name`, `party`, `_state as state`, `created_at::timestamp`, `updated_at::timestamp`
Leave `current_role` (VARIANT) as-is — flattening happens in intermediate.

**`stg_openstates__bills.sql`**
`id as bill_id` (PK), `identifier`, `title`, `_state as state`, `session`, `created_at::timestamp`, `updated_at::timestamp`
Leave `classification`, `sponsorships`, `actions`, `votes`, `versions` as-is — those go in intermediate.

**`stg_census__congressional_districts.sql`**
Rename Census API fields (uppercase in raw) and cast demographics to int.
`"NAME" as district_name`, `"STATE" as state_fips`, `"CONGRESSIONAL_DISTRICT" as district_number`
`total_population::int`, `median_household_income::int`, `pop_white_alone::int`, `pop_black_alone::int`, `pop_hispanic_latino::int`, `pop_bachelors_degree::int`, `pop_health_insurance::int`
No surrogate key — computed keys belong in intermediate.

**`stg_census__states.sql`**
`"NAME" as state_name`, `"STATE" as state_fips` (PK), same demographic casts as above.

---

### 3. `src/dbt/models/staging/_stg_models.yml`
For each of the 9 models:
- Model-level `description` (source system, grain, what renames/casts were applied)
- **Column-level descriptions for every selected field** — plain English, civic/legislative context, not just restating the name
- Tests: `unique` + `not_null` on all primary keys; `not_null` on key dimension fields (state, name, etc.)
- `accepted_values` where applicable

---

### 4. `src/dbt/dbt_project.yml` — add `persist_docs`
Add `+persist_docs` to the staging block so dbt pushes model + column descriptions into Snowflake as table/column comments on every `dbt run`:

```yaml
models:
  civiclens:
    staging:
      +materialized: view
      +persist_docs:
        relation: true
        columns: true
```

One source of truth — dbt YAML drives both dbt docs and Snowflake column comments.

---

### 5. `profiles.yml` (documentation only — gitignored)
Not created by this plan. User must create `~/.dbt/profiles.yml` locally:
```yaml
civiclens:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      private_key_path: "{{ env_var('SNOWFLAKE_PRIVATE_KEY_PATH') }}"
      role: CIVICLENS
      warehouse: CIVICLENS_WH
      database: CIVICLENS
      schema: STAGING
```

---

## What's Deferred to Intermediate
These transformations are intentionally out of scope for this plan:
- UNION of `stg_congress__house_committees` + `stg_congress__senate_committees` → `int_congress__committees`
- Flattening `current_role` VARIANT from OpenStates people
- Extracting `classification[0]` and `sponsorships` from OpenStates bills
- Flattening `terms` array from Congress members
- Surrogate PK for census congressional districts

---

## Verification
```bash
cd src/dbt

# Verify connection (requires .env + profiles.yml)
dbt debug

# Verify SQL compiles (no Snowflake data needed)
dbt compile --select staging

# Run and test once raw data exists
dbt run --select staging
dbt test --select staging
```
