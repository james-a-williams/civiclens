with crosswalk as (
    select * from {{ ref('int_persons__id_crosswalk') }}
),

state_map as (
    select state_name, state_abbr from {{ ref('state_abbreviations') }}
),

federal as (
    select
        x.person_key,
        m.bioguide_id                                   as legislator_id,
        m.member_name                                   as name,
        m.party,
        'federal'                                       as level,
        s.state_abbr                                    as state,
        iff(m.district is null, 'senate', 'house')      as chamber,
        m.district::int                                 as district,
        iff(m.district is null, 'Senator', 'Representative') as title
    from {{ ref('stg_congress__members') }} m
    left join state_map s on s.state_name = m.state
    left join crosswalk x on x.bioguide_id = m.bioguide_id
),

state as (
    select
        x.person_key,
        p.openstates_id                                 as legislator_id,
        p.name,
        p.party,
        'state'                                         as level,
        upper(p.state)                                  as state,
        case p.current_role:org_classification::string
            when 'upper' then 'senate'
            when 'lower' then 'house'
        end                                             as chamber,
        try_to_number(p.current_role:district::string)  as district,
        p.current_role:title::string                    as title
    from {{ ref('stg_openstates__people') }} p
    left join crosswalk x on x.openstates_id = p.openstates_id
)

select * from federal
union all
select * from state
