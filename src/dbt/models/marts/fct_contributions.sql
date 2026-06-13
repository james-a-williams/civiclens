{# One row per contribution transaction, unified across sources.

   NYC CFB is the only transaction-grain source today; the schema is designed
   for FEC Schedule A ('fec_sa') to union in during Phase 3. CFB refno is not
   unique across rows, so the surrogate key adds a dedup sequence over the
   natural columns — deterministic for a given raw snapshot. #}

with crosswalk as (
    select * from {{ ref('int_persons__id_crosswalk') }}
),

cfb as (
    select
        *,
        row_number() over (
            partition by transaction_ref, recipient_id, election_cycle,
                         contribution_date, contributor_name, amount
            order by load_at
        ) as dedup_seq
    from {{ ref('stg_nyc_cfb__contributions') }}
    where office_code != 'IS'
)

select
    md5(concat_ws('|',
        coalesce(c.transaction_ref, ''),
        c.recipient_id,
        c.election_cycle::string,
        coalesce(c.contribution_date::string, ''),
        coalesce(c.contributor_name, ''),
        c.amount::string,
        c.dedup_seq::string
    ))                                          as contribution_key,
    {{ candidacy_key('nyc_cfb', 'c.recipient_id', 'c.election_cycle') }} as candidacy_key,
    x.person_key,
    {{ donor_key('c.contributor_name', 'c.zip', 'c.employer_name') }} as donor_key,
    'nyc_cfb'                                   as source_system,
    c.election_cycle                            as cycle,
    c.contribution_date,
    c.amount,
    c.matchable_amount,
    c.contributor_name,
    c.contributor_type,
    c.employer_name,
    c.occupation,
    c.city,
    c.state,
    c.zip,
    c.payment_method,
    c.recipient_id,
    c.recipient_name
from cfb c
left join crosswalk x on x.nyc_cfb_recipient_id = c.recipient_id
