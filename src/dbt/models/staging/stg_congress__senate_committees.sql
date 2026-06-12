select
    systemcode      as committee_code,
    name            as committee_name,
    url
from {{ source('raw', 'senate_committees') }}
where systemcode is not null
