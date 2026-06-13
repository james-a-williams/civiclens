select
    v.congress::integer                     as congress,
    v.session::integer                      as session,
    v.chamber,
    v.vote_number::integer                  as vote_number,
    v.legis_num,
    v.vote_question,
    v.vote_result,
    v.vote_date::timestamp                  as vote_date,
    mv.value:lis_member_id::string          as lis_member_id,
    mv.value:name::string                   as voter_name,
    mv.value:party::string                  as party,
    mv.value:state::string                  as state,
    mv.value:option::string                 as vote_option,
    v.load_at
from {{ source('raw', 'congress_senate_votes') }} v,
    lateral flatten(input => v.member_votes) mv
where v.congress is not null
  and v.member_votes is not null
