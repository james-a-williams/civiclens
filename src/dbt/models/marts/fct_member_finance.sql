{# Finance totals for elected federal officials, one row per (member, cycle).
   Joins via fec_candidate_id so members who ran multiple times across cycles
   are correctly matched. Only includes federal office types (H, S, P). #}

select
    m.member_key,
    m.bioguide_id,
    f.candidate_id      as fec_candidate_id,
    f.cycle,
    f.total_receipts,
    f.total_disbursements,
    f.cash_on_hand,
    f.individual_itemized_contributions,
    f.individual_unitemized_contributions,
    f.pac_contributions,
    f.party_contributions,
    f.candidate_self_funding,
    -- Derived signals used by COI scoring
    round(div0(f.pac_contributions, f.total_receipts) * 100, 1)
                        as pac_pct_of_total,
    round(div0(
        f.individual_itemized_contributions + f.individual_unitemized_contributions,
        f.total_receipts
    ) * 100, 1)         as individual_pct_of_total
from {{ ref('stg_fec__candidate_totals') }} f
join {{ ref('dim_members') }} m
    on m.fec_candidate_id = f.candidate_id
where f.office in ('H', 'S')   -- House and Senate only
