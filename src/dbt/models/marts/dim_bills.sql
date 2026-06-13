{# One row per bill, unified across state (OpenStates) and federal (Congress.gov).

   bill_key is the stable join target for fct_bill_sponsorships and fct_votes.
   OpenStates bills have an opaque OCD bill_id as the source key; Congress bills
   use congress:bill_type:bill_number. bill_type is null for state bills — state
   type prefixes are embedded in the identifier (e.g. "HB 123", "SR 7"). #}

with openstates as (
    select
        md5('openstates:' || bill_id)   as bill_key,
        bill_id                         as source_bill_id,
        'openstates'                    as source_system,
        'state'                         as level,
        upper(state)                    as state,
        null::integer                   as congress,
        session,
        null                            as bill_type,
        identifier,
        title,
        abstract,
        openstates_url                  as url,
        null::date                      as latest_action_date,
        null                            as latest_action_text,
        updated_at::date                as update_date
    from {{ ref('stg_openstates__bills') }}
),

congress_bills as (
    select
        md5('congress:' || congress::string || ':' || lower(bill_type) || ':' || bill_number) as bill_key,
        lower(bill_type) || bill_number as source_bill_id,
        'congress'                      as source_system,
        'federal'                       as level,
        null                            as state,
        congress,
        null                            as session,
        upper(bill_type)                as bill_type,
        upper(bill_type) || ' ' || bill_number as identifier,
        title,
        null                            as abstract,
        api_url                         as url,
        latest_action_date,
        latest_action_text,
        update_date
    from {{ ref('stg_congress__bills') }}
)

select * from openstates
union all
select * from congress_bills
