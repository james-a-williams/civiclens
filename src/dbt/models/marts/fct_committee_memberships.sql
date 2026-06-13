with members as (
    select member_key, bioguide_id from {{ ref('dim_members') }}
),

memberships as (
    select * from {{ ref('stg_congress__committee_memberships') }}
),

industry_map as (
    select * from {{ ref('congressional_committee_industry_map') }}
)

select
    m.member_key,
    cm.congress,
    cm.chamber,
    cm.committee_code,
    cm.committee_name,
    cm.role_title,
    cm.rank,
    -- Best-match industry category via keyword lookup (first match wins)
    min(im.industry_category)                   as industry_category
from memberships cm
join members m on m.bioguide_id = cm.bioguide_id
left join industry_map im
    on lower(cm.committee_name) ilike '%' || lower(im.committee_keyword) || '%'
group by
    m.member_key, cm.congress, cm.chamber,
    cm.committee_code, cm.committee_name, cm.role_title, cm.rank
