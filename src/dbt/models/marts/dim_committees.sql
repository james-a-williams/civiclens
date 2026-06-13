select
    committee_id,
    name,
    committee_type,
    committee_type_full,
    designation,
    case designation
        when 'A' then 'Authorized by candidate'
        when 'B' then 'Lobbyist/registrant PAC'
        when 'D' then 'Leadership PAC'
        when 'J' then 'Joint fundraising committee'
        when 'P' then 'Principal campaign committee'
        when 'U' then 'Unauthorized'
        else designation
    end                  as designation_full,
    state,
    party,
    organization_type,
    case organization_type
        when 'C' then 'Corporation'
        when 'L' then 'Labor organization'
        when 'M' then 'Membership organization'
        when 'T' then 'Trade association'
        when 'V' then 'Cooperative'
        when 'W' then 'Corporation without capital stock'
        else organization_type
    end                  as organization_type_full,
    filing_frequency
from {{ ref('stg_fec__committees') }}
