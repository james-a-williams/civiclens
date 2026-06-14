select
    id                              as bill_id,
    identifier,
    title,
    null::varchar                   as abstract,
    openstates_url,
    _state                          as state,
    session,
    created_at::timestamp           as created_at,
    updated_at::timestamp           as updated_at
from {{ source('raw', 'bills') }}
where id is not null
