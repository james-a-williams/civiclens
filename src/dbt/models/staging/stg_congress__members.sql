select
    bioguideid                                  as bioguide_id,
    name                                        as member_name,
    partyname                                   as party,
    state,
    district,
    -- terms is a VARIANT array; pull the most recent congress number and chamber
    terms[0]:congress::int                      as latest_congress,
    iff(district is null, 'senate', 'house')    as chamber,
    -- FEC candidate ID lives in identifiers VARIANT when populated by the connector
    identifiers:fec::string                     as fec_candidate_id,
    updatedate::date                            as updated_at
from {{ source('raw', 'members') }}
where bioguideid is not null
