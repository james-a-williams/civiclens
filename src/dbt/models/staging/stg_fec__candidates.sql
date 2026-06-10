select
    candidate_id,
    name,
    office,
    office_full,
    state,
    district,
    party,
    party_full,
    election_year::int           as election_year,
    incumbent_challenge,
    has_raised_funds::boolean    as has_raised_funds,
    load_date::date              as load_date
from {{ source('raw', 'candidates') }}
where candidate_id is not null
