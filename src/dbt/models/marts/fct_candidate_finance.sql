{# One row per candidacy per cycle, with finance fields populated per the
   coverage of each source system. Nulls are intentional: FEC has no donor
   stats until Schedule A lands (Phase 3); NY BOE publishes only public funds
   and qualified expenditures; NYC CFB has contributions but no disbursements. #}

with fec as (
    select
        {{ candidacy_key('fec', 'candidate_id', 'cycle') }} as candidacy_key,
        'fec'                       as coverage,
        total_receipts              as total_raised,
        total_disbursements         as total_spent,
        cash_on_hand,
        null                        as public_funds_received,
        null                        as matchable_amount_total,
        null                        as contribution_count,
        null                        as unique_donor_count,
        null                        as avg_contribution,
        null                        as pct_small_dollar
    from {{ ref('stg_fec__candidate_totals') }}
),

-- Grain and key construction must stay in sync with dim_candidates: filer x
-- year x office, longest name wins. Gov/Lt-Gov tickets share a committee, so
-- committee-level amounts appear on both ticket members' candidacies.
ny_boe as (
    select
        {{ candidacy_key('ny_boe', "filer_id || ':' || office", 'election_year') }} as candidacy_key,
        'ny_boe'                            as coverage,
        null                                as total_raised,
        qualified_campaign_expenditures     as total_spent,
        null                                as cash_on_hand,
        public_funds_received,
        null                                as matchable_amount_total,
        null                                as contribution_count,
        null                                as unique_donor_count,
        null                                as avg_contribution,
        null                                as pct_small_dollar
    from {{ ref('stg_ny_boe__activity') }}
    qualify row_number() over (
        partition by filer_id, election_year, office
        order by length(candidate_name) desc
    ) = 1
),

nyc_cfb as (
    select
        candidacy_key,
        'nyc_cfb'                           as coverage,
        sum(amount)                         as total_raised,
        null                                as total_spent,
        null                                as cash_on_hand,
        null                                as public_funds_received,
        sum(matchable_amount)               as matchable_amount_total,
        count(*)                            as contribution_count,
        count(distinct donor_key)           as unique_donor_count,
        round(avg(amount), 2)               as avg_contribution,
        round(div0(
            sum(iff(amount < 200, amount, 0)), sum(amount)
        ), 3)                               as pct_small_dollar
    from {{ ref('fct_contributions') }}
    where source_system = 'nyc_cfb'
    group by candidacy_key
)

select * from fec
union all
select * from ny_boe
union all
select * from nyc_cfb
