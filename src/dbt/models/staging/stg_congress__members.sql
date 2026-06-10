select
    "bioguideId"         as bioguide_id,
    name                 as member_name,
    "partyName"          as party,
    state,
    district,
    "updateDate"::date   as updated_at
from {{ source('raw', 'members') }}
where "bioguideId" is not null
