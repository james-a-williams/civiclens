{# One row per candidacy: person x office sought x cycle.

   FEC rows are pinned to the cycle the loader fetched (fec_cycle var) because
   stg_fec__candidates carries no cycle column. NYC CFB office codes follow the
   CFB data library coding; doubled codes (11, 22, ...) are the same office
   as their first digit. 'IS' (independent spenders) are excluded — they are
   not candidate committees. #}

with crosswalk as (
    select * from {{ ref('int_persons__id_crosswalk') }}
),

fec as (
    select
        {{ candidacy_key('fec', 'c.candidate_id', var('fec_cycle', 2024)) }} as candidacy_key,
        x.person_key,
        -- FEC names are 'LAST, FIRST': flip for display
        initcap(
            trim(substr(c.name, position(',' in c.name) + 1))
            || ' ' || trim(split_part(c.name, ',', 1))
        )                                   as display_name,
        c.party_full                        as party,
        'federal'                           as level,
        c.office_full                       as office,
        c.state,
        try_to_number(c.district)           as district,
        {{ var('fec_cycle', 2024) }}        as cycle,
        c.incumbent_challenge,
        c.incumbent_challenge = 'I'         as is_incumbent,
        'fec'                               as source_system,
        c.candidate_id                      as source_id
    from {{ ref('stg_fec__candidates') }} c
    left join crosswalk x on x.fec_candidate_id = c.candidate_id
),

-- Grain: filer x year x office. Gov/Lt-Gov tickets share one filer_id, and the
-- BOE files contain name-variant duplicates (keep the longest name).
-- Key construction must stay in sync with fct_candidate_finance.
ny_boe as (
    select
        {{ candidacy_key('ny_boe', "a.filer_id || ':' || a.office", 'a.election_year') }} as candidacy_key,
        x.person_key,
        a.candidate_name                    as display_name,
        null                                as party,
        'state'                             as level,
        a.office,
        'NY'                                as state,
        try_to_number(a.district::string)   as district,
        a.election_year                     as cycle,
        null                                as incumbent_challenge,
        x.openstates_id is not null         as is_incumbent,
        'ny_boe'                            as source_system,
        a.filer_id::string                  as source_id
    from {{ ref('stg_ny_boe__activity') }} a
    left join crosswalk x on x.ny_boe_filer_id = a.filer_id
    qualify row_number() over (
        partition by a.filer_id, a.election_year, a.office
        order by length(a.candidate_name) desc
    ) = 1
),

nyc_cfb as (
    select
        {{ candidacy_key('nyc_cfb', 'c.recipient_id', 'c.election_cycle') }} as candidacy_key,
        x.person_key,
        max(c.recipient_name)               as display_name,
        null                                as party,
        'local'                             as level,
        case left(max(c.office_code), 1)
            when '1' then 'Mayor'
            when '2' then 'Public Advocate'
            when '3' then 'Comptroller'
            when '4' then 'Borough President'
            when '5' then 'City Council'
            else 'Undeclared'
        end                                 as office,
        'NY'                                as state,
        null                                as district,
        c.election_cycle                    as cycle,
        null                                as incumbent_challenge,
        null                                as is_incumbent,
        'nyc_cfb'                           as source_system,
        c.recipient_id                      as source_id
    from {{ ref('stg_nyc_cfb__contributions') }} c
    left join crosswalk x on x.nyc_cfb_recipient_id = c.recipient_id
    where c.office_code != 'IS'
    group by c.recipient_id, c.election_cycle, x.person_key
)

select * from fec
union all
select * from ny_boe
union all
select * from nyc_cfb
