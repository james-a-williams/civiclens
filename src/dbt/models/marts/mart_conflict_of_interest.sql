{# Conflict of interest score for elected federal officials.

   Score (0–100): percentage of total fundraising that came from PACs and
   political committees. Higher = more dependent on organized money vs. grassroots.

   Risk tiers:
     High   (>=60): majority of funding from PACs
     Medium (>=30): significant PAC dependency
     Low    (<30):  primarily individual-donor funded

   Evidence description: plain-language summary of PAC total, %, and which
   committee jurisdictions overlap with significant funding sources.

   Phase 3 enhancement: break pac_contributions down by donor org industry
   once FEC Schedule A (itemized receipts) is loaded into raw.schedule_a. #}

with finance as (
    select
        member_key,
        cycle,
        total_receipts,
        pac_contributions,
        individual_itemized_contributions,
        individual_unitemized_contributions,
        party_contributions,
        candidate_self_funding,
        pac_pct_of_total
    from {{ ref('fct_member_finance') }}
    where total_receipts > 0
),

committee_context as (
    -- Aggregate the committees a member sits on and their regulated industries
    -- for the most recent congress available
    select
        member_key,
        listagg(distinct committee_name, ' · ')
            within group (order by committee_name)         as committees_served,
        listagg(distinct industry_category, ' · ')
            within group (order by industry_category)      as regulated_industries
    from {{ ref('fct_committee_memberships') }}
    group by member_key
),

scored as (
    select
        f.member_key,
        f.cycle,
        f.total_receipts,
        f.pac_contributions,
        f.individual_itemized_contributions,
        f.individual_unitemized_contributions,
        f.party_contributions,
        f.candidate_self_funding,
        f.pac_pct_of_total                              as coi_score,
        case
            when f.pac_pct_of_total >= 60 then 'High'
            when f.pac_pct_of_total >= 30 then 'Medium'
            else 'Low'
        end                                             as risk_level,
        cc.committees_served,
        cc.regulated_industries,
        -- Plain-language evidence the UI can display alongside the score
        'Received $' || to_varchar(round(f.pac_contributions, 0), '999,999,999')
            || ' from PACs and political committees ('
            || to_varchar(f.pac_pct_of_total) || '% of $'
            || to_varchar(round(f.total_receipts, 0), '999,999,999')
            || ' total raised in ' || f.cycle::string || '). '
            || iff(
                cc.committees_served is not null,
                'Sits on: ' || cc.committees_served || '. '
                    || 'These committees oversee: ' || cc.regulated_industries || '.',
                'No committee assignment data available yet.'
            )                                           as evidence_description
    from finance f
    left join committee_context cc on cc.member_key = f.member_key
)

select
    member_key,
    cycle,
    coi_score,
    risk_level,
    total_receipts,
    pac_contributions,
    individual_itemized_contributions,
    individual_unitemized_contributions,
    party_contributions,
    candidate_self_funding,
    committees_served,
    regulated_industries,
    evidence_description
from scored
