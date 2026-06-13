{# One row per FEC candidacy: person x federal office x cycle.
   Scope: federal offices only (House, Senate). State and local candidacies
   removed in scope pivot to federal-officials-only focus.
   Use dim_members for a person-centric view across all congresses served. #}

with crosswalk as (
    select * from {{ ref('int_persons__id_crosswalk') }}
)

select
    {{ candidacy_key('fec', 'c.candidate_id', 'f.cycle') }} as candidacy_key,
    x.person_key,
    initcap(
        trim(substr(c.name, position(',' in c.name) + 1))
        || ' ' || trim(split_part(c.name, ',', 1))
    )                                   as display_name,
    c.party_full                        as party,
    'federal'                           as level,
    c.office_full                       as office,
    c.state,
    try_to_number(c.district)           as district,
    f.cycle,
    c.incumbent_challenge,
    c.incumbent_challenge = 'I'         as is_incumbent,
    'fec'                               as source_system,
    c.candidate_id                      as source_id
from {{ ref('stg_fec__candidates') }} c
join {{ ref('stg_fec__candidate_totals') }} f on f.candidate_id = c.candidate_id
left join crosswalk x on x.fec_candidate_id = c.candidate_id
where c.office in ('H', 'S')
