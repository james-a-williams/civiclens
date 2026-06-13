{# Finance summary per FEC candidacy (federal offices only).
   One row per (candidate_id, cycle). Joins to dim_candidates on candidacy_key. #}

select
    {{ candidacy_key('fec', 'candidate_id', 'cycle') }}     as candidacy_key,
    'fec'                                                   as coverage,
    total_receipts                                          as total_raised,
    total_disbursements                                     as total_spent,
    cash_on_hand,
    null                                                    as public_funds_received,
    null                                                    as matchable_amount_total,
    null                                                    as contribution_count,
    null                                                    as unique_donor_count,
    null                                                    as avg_contribution,
    null                                                    as pct_small_dollar
from {{ ref('stg_fec__candidate_totals') }}
where office in ('H', 'S')
