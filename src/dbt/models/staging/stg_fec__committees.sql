select
    committee_id,
    name,
    committee_type,
    committee_type_full,
    designation,
    state,
    party,
    cycle::int          as cycle,
    organization_type,
    filing_frequency
from {{ source('raw', 'committees') }}
where committee_id is not null
