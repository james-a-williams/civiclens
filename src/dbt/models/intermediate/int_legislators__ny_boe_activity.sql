with activity as (
    select * from {{ ref('stg_ny_boe__activity') }}
),

legislators as (
    select
        openstates_id,
        name                                as legislator_name,
        party                               as legislator_party,
        current_role:district::string       as district,
        split_part(name, ' ', -1)           as last_name
    from {{ ref('stg_openstates__people') }}
    where current_role is not null
)

select
    activity.*,
    legislators.openstates_id,
    legislators.legislator_name,
    legislators.legislator_party
from activity
left join legislators
    on jarowinkler_similarity(
           upper(trim(split_part(activity.candidate_name, ' ', -1))),
           upper(trim(legislators.last_name))
       ) >= 85
   and activity.district::string = legislators.district
   and (
       activity.office ilike '%assembly%'
       or activity.office ilike '%senate%'
   )
