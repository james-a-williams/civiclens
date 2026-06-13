select
    b.id                                as bill_id,
    s.value:name::string                as sponsor_name,
    s.value:entity_type::string         as entity_type,
    s.value:primary::boolean            as is_primary,
    s.value:classification::string      as classification,
    s.value:person:id::string           as openstates_person_id,
    b.load_at
from {{ source('raw', 'bills') }} b,
    lateral flatten(input => b.sponsorships) s
where b.id is not null
  and b.sponsorships is not null
