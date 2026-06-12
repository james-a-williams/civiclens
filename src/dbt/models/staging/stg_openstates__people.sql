select
    id                      as openstates_id,
    name,
    party,
    _state                  as state,
    current_role,
    created_at::timestamp   as created_at,
    updated_at::timestamp   as updated_at
from {{ source('raw', 'people') }}
where id is not null
