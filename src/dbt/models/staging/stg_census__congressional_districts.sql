select
    name                        as district_name,
    state                       as state_fips,
    congressional_district      as district_number,
    total_population::int       as total_population,
    median_household_income::int as median_household_income,
    pop_white_alone::int        as pop_white_alone,
    pop_black_alone::int        as pop_black_alone,
    pop_hispanic_latino::int    as pop_hispanic_latino,
    pop_bachelors_degree::int   as pop_bachelors_degree,
    pop_health_insurance::int   as pop_health_insurance
from {{ source('raw', 'congressional_districts') }}
where state is not null
  and congressional_district is not null
