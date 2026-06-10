select
    "systemCode"    as committee_code,
    "name"          as committee_name,
    "url"           as url
from {{ source('raw', 'house_committees') }}
where "systemCode" is not null
