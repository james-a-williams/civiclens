select
    election::int               as election_cycle,
    cycle_year::int             as cycle_year,
    recipid                     as recipient_id,
    recipname                   as recipient_name,
    officecd                    as office_code,
    filing                      as filing_period,
    schedule,
    refno                       as transaction_ref,
    date::date                  as contribution_date,
    name                        as contributor_name,
    c_code                      as contributor_type,
    city,
    state,
    zip,
    occupation,
    empname                     as employer_name,
    amnt::decimal               as amount,
    matchamnt::decimal          as matchable_amount,
    pay_method                  as payment_method,
    load_at::timestamp_tz       as load_at
from {{ source('raw', 'nyc_cfb_contributions') }}
where amnt is not null
  and amnt::decimal > 0
