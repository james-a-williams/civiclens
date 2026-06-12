{# One row per resolved person across all source ID systems.

   Match strategy mirrors int_legislators__ny_boe_activity: exact match on
   geography (state / district / office level) first, Jaro-Winkler >= 85 on
   last name as the fuzzy component. Match provenance is kept on every row
   so scores are auditable.

   Levels are resolved independently (federal / state / local) — cross-level
   identity (e.g. a NYC mayor who was once governor) is out of scope until
   Phase 5. #}

with members as (
    select
        bioguide_id,
        member_name,
        state                                        as state_name,
        district::int                                as district,
        upper(trim(split_part(member_name, ',', 1))) as last_name
    from {{ ref('stg_congress__members') }}
),

state_map as (
    select state_name, state_abbr from {{ ref('state_abbreviations') }}
),

fed_members as (
    select members.*, state_map.state_abbr
    from members
    left join state_map using (state_name)
),

fec_candidates as (
    select
        candidate_id                          as fec_candidate_id,
        name                                  as fec_name,
        office,
        state,
        try_to_number(district)               as district,
        upper(trim(split_part(name, ',', 1))) as last_name
    from {{ ref('stg_fec__candidates') }}
),

-- House candidates match members on state + district; Senate on state alone
-- (members have null district for senators). Presidential candidates never match.
fed_match_pairs as (
    select
        m.bioguide_id,
        f.fec_candidate_id,
        jarowinkler_similarity(m.last_name, f.last_name) as score
    from fed_members m
    join fec_candidates f
      on f.state = m.state_abbr
     and jarowinkler_similarity(m.last_name, f.last_name) >= 85
     and (
         (f.office = 'H' and m.district is not null and f.district = m.district)
         or (f.office = 'S' and m.district is null)
     )
),

fed_matches as (
    -- best candidate per member, then enforce one member per candidate
    select * from (
        select *
        from fed_match_pairs
        qualify row_number() over (
            partition by bioguide_id order by score desc, fec_candidate_id
        ) = 1
    )
    qualify row_number() over (
        partition by fec_candidate_id order by score desc, bioguide_id
    ) = 1
),

federal_persons as (
    select
        {{ person_key('bioguide', 'm.bioguide_id') }} as person_key,
        m.member_name                                 as canonical_name,
        'federal'                                     as level,
        m.bioguide_id,
        x.fec_candidate_id,
        null                                          as openstates_id,
        null                                          as ny_boe_filer_id,
        null                                          as nyc_cfb_recipient_id,
        iff(x.fec_candidate_id is not null, 'state_district_jarowinkler', null) as match_method,
        x.score                                       as match_confidence
    from fed_members m
    left join fed_matches x using (bioguide_id)
),

fec_only_persons as (
    select
        {{ person_key('fec', 'f.fec_candidate_id') }} as person_key,
        f.fec_name                                    as canonical_name,
        'federal'                                     as level,
        null                                          as bioguide_id,
        f.fec_candidate_id,
        null                                          as openstates_id,
        null                                          as ny_boe_filer_id,
        null                                          as nyc_cfb_recipient_id,
        null                                          as match_method,
        null                                          as match_confidence
    from fec_candidates f
    where not exists (
        select 1 from fed_matches x where x.fec_candidate_id = f.fec_candidate_id
    )
),

-- NY BOE <-> OpenStates matches come from the existing fuzzy-match model;
-- dedupe to one filer per person and one person per filer.
ny_boe_links as (
    select * from (
        select distinct filer_id, openstates_id
        from {{ ref('int_legislators__ny_boe_activity') }}
        where openstates_id is not null
        qualify row_number() over (partition by openstates_id order by filer_id) = 1
    )
    qualify row_number() over (partition by filer_id order by openstates_id) = 1
),

state_persons as (
    select
        {{ person_key('openstates', 'p.openstates_id') }} as person_key,
        p.name                                            as canonical_name,
        'state'                                           as level,
        null                                              as bioguide_id,
        null                                              as fec_candidate_id,
        p.openstates_id,
        l.filer_id                                        as ny_boe_filer_id,
        null                                              as nyc_cfb_recipient_id,
        iff(l.filer_id is not null, 'district_jarowinkler', null) as match_method,
        null                                              as match_confidence
    from {{ ref('stg_openstates__people') }} p
    left join ny_boe_links l using (openstates_id)
),

ny_boe_only_persons as (
    select
        {{ person_key('nyboe', 'a.filer_id') }} as person_key,
        a.candidate_name                        as canonical_name,
        'state'                                 as level,
        null                                    as bioguide_id,
        null                                    as fec_candidate_id,
        null                                    as openstates_id,
        a.filer_id                              as ny_boe_filer_id,
        null                                    as nyc_cfb_recipient_id,
        null                                    as match_method,
        null                                    as match_confidence
    from {{ ref('stg_ny_boe__activity') }} a
    where not exists (
        select 1 from ny_boe_links l where l.filer_id = a.filer_id
    )
    -- One person per filer. Gov/Lt-Gov tickets share a filer_id: the
    -- Governor-line name becomes canonical (committee-level identity —
    -- a known Phase 1 limitation).
    qualify row_number() over (
        partition by a.filer_id
        order by iff(a.office = 'Governor', 0, 1), a.election_year desc,
                 length(a.candidate_name) desc
    ) = 1
),

-- office_code 'IS' rows are independent spenders, not candidate committees
nyc_cfb_persons as (
    select
        {{ person_key('nyccfb', 'recipient_id') }} as person_key,
        max(recipient_name)                        as canonical_name,
        'local'                                    as level,
        null                                       as bioguide_id,
        null                                       as fec_candidate_id,
        null                                       as openstates_id,
        null                                       as ny_boe_filer_id,
        recipient_id                               as nyc_cfb_recipient_id,
        null                                       as match_method,
        null                                       as match_confidence
    from {{ ref('stg_nyc_cfb__contributions') }}
    where office_code != 'IS'
    group by recipient_id
)

select * from federal_persons
union all
select * from fec_only_persons
union all
select * from state_persons
union all
select * from ny_boe_only_persons
union all
select * from nyc_cfb_persons
