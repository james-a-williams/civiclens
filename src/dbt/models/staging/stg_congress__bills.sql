select
    congress::integer                       as congress,
    type                                    as bill_type,
    number                                  as bill_number,
    title,
    originchamber                           as origin_chamber,
    url                                     as api_url,
    latestaction:actionDate::date           as latest_action_date,
    latestaction:text::string               as latest_action_text,
    updatedate::date                        as update_date,
    load_at
from {{ source('raw', 'congress_bills') }}
where congress is not null
