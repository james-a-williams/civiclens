{# One row per elected federal official (unique bioguide_id).
   Represents the person, not any single candidacy or term.
   Join to fct_member_finance on fec_candidate_id for fundraising data.
   Join to fct_committee_memberships on member_key for committee assignments.
   Join to fct_bill_sponsorships / fct_votes on member_key via int_persons__id_crosswalk. #}

with crosswalk as (
    select * from {{ ref('int_persons__id_crosswalk') }}
),

state_map as (
    select state_name, state_abbr from {{ ref('state_abbreviations') }}
),

members as (
    select
        m.bioguide_id,
        m.member_name                                       as name,
        m.party,
        s.state_abbr                                        as state,
        m.chamber,
        m.district::int                                     as district,
        iff(m.chamber = 'senate', 'Senator', 'Representative') as title,
        m.latest_congress,
        m.fec_candidate_id,
        m.updated_at
    from {{ ref('stg_congress__members') }} m
    left join state_map s on s.state_name = m.state
)

select
    x.person_key                                            as member_key,
    m.bioguide_id,
    coalesce(x.fec_candidate_id, m.fec_candidate_id)       as fec_candidate_id,
    m.name,
    m.party,
    m.state,
    m.chamber,
    m.district,
    m.title,
    m.latest_congress,
    -- convenience display: "Rep. Jane Smith (D-NY-14)" or "Sen. Jane Smith (D-NY)"
    m.title || ' ' || m.name
        || ' (' || left(m.party, 1) || '-' || m.state
        || iff(m.chamber = 'house' and m.district is not null,
               '-' || m.district::string, '')
        || ')'                                              as display_name,
    m.updated_at
from members m
left join crosswalk x on x.bioguide_id = m.bioguide_id
