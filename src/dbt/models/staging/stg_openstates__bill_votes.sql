select
    b.id                                    as bill_id,
    ve.value:id::string                     as vote_event_id,
    ve.value:motion_text::string            as motion_text,
    ve.value:result::string                 as result,
    ve.value:start_date::date               as vote_date,
    v.value:voter_name::string              as voter_name,
    v.value:voter:id::string                as openstates_person_id,
    v.value:option::string                  as vote_option,
    b.load_at
from {{ source('raw', 'bills') }} b,
    lateral flatten(input => b.votes) ve,
    lateral flatten(input => ve.value:votes) v
where b.id is not null
  and b.votes is not null
  and ve.value:votes is not null
