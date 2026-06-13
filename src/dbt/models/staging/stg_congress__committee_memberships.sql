{# Committee membership assignments per member per congress.
   Source: raw.congress_committee_memberships, loaded by
   CongressAPIConnector.get_committee_memberships() — see TODO in congress_api.py. #}

select
    bioguide_id,
    congress::int                           as congress,
    chamber,
    committee_code,
    committee_name,
    subcommittee_code,
    subcommittee_name,
    rank::int                               as rank,
    title                                   as role_title
from {{ source('raw', 'congress_committee_memberships') }}
where bioguide_id is not null
  and subcommittee_code is null  -- full committees only; subcommittees filtered out
