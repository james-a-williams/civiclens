{# One row per person × bill sponsorship, unified across state and federal.

   OpenStates: primary/cosponsor distinction is explicit (is_primary flag).
   Congress: the /member/{id}/sponsored-legislation endpoint returns all bills
   a member touched (primary + cosponsor) without distinguishing — is_primary
   is null for Congress rows, a known data gap until per-bill detail is fetched.

   Organization sponsors (entity_type != 'person') are excluded; those rows
   have no openstates_person_id and cannot resolve to a person_key. #}

with crosswalk as (
    select * from {{ ref('int_persons__id_crosswalk') }}
),

bills as (
    select bill_key, source_bill_id, source_system, congress, bill_type, bill_number
    from {{ ref('dim_bills') }}
),

openstates as (
    select
        b.bill_key,
        x.person_key,
        s.sponsor_name,
        'openstates'        as source_system,
        s.is_primary,
        s.classification,
        null::date          as introduced_date
    from {{ ref('stg_openstates__bill_sponsorships') }} s
    left join bills b
        on b.source_bill_id = s.bill_id and b.source_system = 'openstates'
    left join crosswalk x on x.openstates_id = s.openstates_person_id
    where s.entity_type = 'person'
),

congress as (
    select
        b.bill_key,
        x.person_key,
        null                as sponsor_name,
        'congress'          as source_system,
        null::boolean       as is_primary,
        null                as classification,
        s.introduced_date
    from {{ ref('stg_congress__bill_sponsorships') }} s
    left join bills b
        on b.source_system = 'congress'
        and b.bill_type = upper(s.bill_type)
        and b.bill_number = s.bill_number
        and b.congress = s.congress
    left join crosswalk x on x.bioguide_id = s.bioguide_id
),

unioned as (
    select * from openstates
    union all
    select * from congress
)

select
    md5(
        coalesce(person_key, '') || ':' ||
        coalesce(bill_key, '') || ':' ||
        source_system
    )                   as sponsorship_key,
    person_key,
    bill_key,
    source_system,
    sponsor_name,
    is_primary,
    classification,
    introduced_date
from unioned
