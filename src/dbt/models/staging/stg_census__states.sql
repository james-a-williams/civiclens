select
    name                        as state_name,
    state                       as state_fips,
    total_population::int       as total_population,
    median_household_income::int as median_household_income,
    pop_white_alone::int        as pop_white_alone,
    pop_black_alone::int        as pop_black_alone,
    pop_hispanic_latino::int    as pop_hispanic_latino,
    pop_bachelors_degree::int   as pop_bachelors_degree,
    pop_health_insurance::int   as pop_health_insurance
from {{ source('raw', 'states') }}
where state is not null
