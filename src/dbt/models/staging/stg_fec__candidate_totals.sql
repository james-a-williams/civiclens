select
    candidate_id,
    cycle::int                                                      as cycle,
    name,
    office,
    office_full,
    state,
    district,
    party_full,
    receipts::decimal(18, 2)                                        as total_receipts,
    disbursements::decimal(18, 2)                                   as total_disbursements,
    cash_on_hand_end_period::decimal(18, 2)                         as cash_on_hand,
    individual_itemized_contributions::decimal(18, 2)               as individual_itemized_contributions,
    null::decimal(18, 2)                                            as individual_unitemized_contributions,
    -- PAC/committee money is the primary COI signal
    other_political_committee_contributions::decimal(18, 2)         as pac_contributions,
    null::decimal(18, 2)                                            as party_contributions,
    null::decimal(18, 2)                                            as candidate_self_funding,
    load_at::timestamp_tz                                           as load_at
from {{ source('raw', 'candidate_totals') }}
where candidate_id is not null
qualify row_number() over (partition by candidate_id, cycle order by load_at desc) = 1
