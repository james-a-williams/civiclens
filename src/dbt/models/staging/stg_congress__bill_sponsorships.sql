select
    _bioguide_id                            as bioguide_id,
    congress::integer                       as congress,
    type                                    as bill_type,
    number                                  as bill_number,
    title,
    introduceddate::date                    as introduced_date,
    policyarea:name::string                 as policy_area,
    latestaction:actionDate::date           as latest_action_date,
    latestaction:text::string               as latest_action_text,
    load_at
from {{ source('raw', 'congress_member_sponsorships') }}
where _bioguide_id is not null
  and congress is not null
