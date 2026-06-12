select
    election_year::int                              as election_year,
    filer_id,
    committee_name,
    candidate_name,
    office,
    district,
    try_to_decimal(public_funds_received)           as public_funds_received,
    try_to_decimal(qualified_campaign_expenditures) as qualified_campaign_expenditures,
    load_at::timestamp_tz                           as load_at
from {{ source('raw', 'ny_boe_activity') }}
where candidate_name is not null
