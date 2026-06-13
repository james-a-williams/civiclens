-- Run once against the CIVICLENS database before starting the API.
-- Creates the APP schema and the bill_summaries table owned by FastAPI.
-- dbt does not manage this table — rows are written at request time.

create schema if not exists app;

create table if not exists app.bill_summaries (
    bill_key        varchar         primary key,
    plain_summary   text            not null,
    eli5            text            not null,
    model_id        varchar         not null,
    generated_at    timestamp_tz    default current_timestamp()
);
