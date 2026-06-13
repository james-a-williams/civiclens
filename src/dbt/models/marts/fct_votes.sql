{# One row per person × roll call, unified across state and federal.

   Source systems:
   - openstates:      state roll calls from OpenStates /bills with include=votes
   - congress_house:  House roll calls from House Clerk XML (bioguide_id resolves cleanly)
   - congress_senate: Senate roll calls from Senate LIS XML (lis_member_id has no crosswalk
                      today — person_key is null for Senate rows, a known Phase 2 gap)

   vote_option is normalized to yes / no / abstain / present across all sources.
   bill_key is null for procedural votes not tied to a bill (e.g. procedural House
   motions, Senate confirmations). voter_name is kept for display and for future
   Senate identity resolution. #}

with crosswalk as (
    select * from {{ ref('int_persons__id_crosswalk') }}
),

bills as (
    select bill_key, source_bill_id, source_system, congress, bill_type, bill_number
    from {{ ref('dim_bills') }}
),

openstates as (
    select
        v.vote_event_id,
        b.bill_key,
        x.person_key,
        v.voter_name,
        'openstates'    as source_system,
        null            as chamber,
        v.vote_date,
        v.vote_option,
        v.result        as vote_result,
        v.motion_text
    from {{ ref('stg_openstates__bill_votes') }} v
    left join bills b
        on b.source_bill_id = v.bill_id and b.source_system = 'openstates'
    left join crosswalk x on x.openstates_id = v.openstates_person_id
),

house as (
    select
        'house:' || v.year::string || ':' || v.roll_number::string  as vote_event_id,
        b.bill_key,
        x.person_key,
        v.voter_name,
        'congress_house'    as source_system,
        v.chamber,
        v.vote_date,
        v.vote_option,
        v.vote_result,
        v.vote_question     as motion_text
    from {{ ref('stg_congress__house_votes') }} v
    left join bills b
        on b.source_system = 'congress'
        and b.bill_type = upper(trim(split_part(v.legis_num, ' ', 1)))
        and b.bill_number = trim(split_part(v.legis_num, ' ', 2))
        and b.congress = v.congress
    left join crosswalk x on x.bioguide_id = v.bioguide_id
),

senate as (
    select
        'senate:' || v.congress::string || ':' || v.session::string
            || ':' || v.vote_number::string                         as vote_event_id,
        b.bill_key,
        null                as person_key,
        v.voter_name,
        'congress_senate'   as source_system,
        v.chamber,
        v.vote_date::date   as vote_date,
        v.vote_option,
        v.vote_result,
        v.vote_question     as motion_text
    from {{ ref('stg_congress__senate_votes') }} v
    left join bills b
        on b.source_system = 'congress'
        and b.bill_type = upper(trim(split_part(v.legis_num, ' ', 1)))
        and b.bill_number = trim(split_part(v.legis_num, ' ', 2))
        and b.congress = v.congress
),

unioned as (
    select * from openstates
    union all
    select * from house
    union all
    select * from senate
)

select
    md5(
        coalesce(person_key, voter_name) || ':' ||
        vote_event_id || ':' ||
        source_system
    )               as vote_key,
    person_key,
    bill_key,
    vote_event_id,
    source_system,
    chamber,
    vote_date,
    vote_option,
    vote_result,
    motion_text,
    voter_name
from unioned
