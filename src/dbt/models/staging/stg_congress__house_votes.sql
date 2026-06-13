select
    v.congress::integer                     as congress,
    v.session::integer                      as session,
    v.chamber,
    v.roll_number::integer                  as roll_number,
    v.year::integer                         as year,
    v.legis_num,
    v.vote_question,
    v.vote_result,
    v.action_date::date                     as vote_date,
    mv.value:bioguide_id::string            as bioguide_id,
    mv.value:name::string                   as voter_name,
    mv.value:party::string                  as party,
    mv.value:state::string                  as state,
    mv.value:option::string                 as vote_option,
    v.load_at
from {{ source('raw', 'congress_house_votes') }} v,
    lateral flatten(input => v.member_votes) mv
where v.congress is not null
  and v.member_votes is not null
