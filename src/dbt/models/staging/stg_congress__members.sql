select
    bioguideid           as bioguide_id,
    name                 as member_name,
    partyname            as party,
    state,
    district,
    updatedate::date     as updated_at
from {{ source('raw', 'members') }}
where bioguideid is not null
