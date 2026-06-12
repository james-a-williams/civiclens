select
    candidate_id,
    name,
    office,
    office_full,
    state,
    district,
    party,
    party_full,
    incumbent_challenge,
    has_raised_funds::boolean    as has_raised_funds,
    load_at::timestamp_tz        as load_at
from {{ source('raw', 'candidates') }}
where candidate_id is not null
