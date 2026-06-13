with state_map as (
    select state_name, state_abbr, state_fips from {{ ref('state_abbreviations') }}
),

districts as (
    select
        'cd-' || d.state_fips || '-' || d.district_number as district_key,
        'congressional_district'                          as geo_level,
        m.state_abbr                                      as state,
        try_to_number(d.district_number)                  as district_number,
        d.district_name                                   as name,
        d.total_population,
        d.median_household_income,
        d.pop_white_alone,
        d.pop_black_alone,
        d.pop_hispanic_latino,
        d.pop_bachelors_degree,
        d.pop_health_insurance
    from {{ ref('stg_census__congressional_districts') }} d
    left join state_map m on m.state_fips = d.state_fips
),

states as (
    select
        'state-' || s.state_fips     as district_key,
        'state'                      as geo_level,
        m.state_abbr                 as state,
        null                         as district_number,
        s.state_name                 as name,
        s.total_population,
        s.median_household_income,
        s.pop_white_alone,
        s.pop_black_alone,
        s.pop_hispanic_latino,
        s.pop_bachelors_degree,
        s.pop_health_insurance
    from {{ ref('stg_census__states') }} s
    left join state_map m on m.state_fips = s.state_fips
),

unioned as (
    select * from districts
    union all
    select * from states
)

select
    *,
    round(div0(pop_white_alone, total_population), 3)      as pct_white,
    round(div0(pop_black_alone, total_population), 3)      as pct_black,
    round(div0(pop_hispanic_latino, total_population), 3)  as pct_hispanic,
    round(div0(pop_bachelors_degree, total_population), 3) as pct_bachelors,
    round(div0(pop_health_insurance, total_population), 3) as pct_insured
from unioned
