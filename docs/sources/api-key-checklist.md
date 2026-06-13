# API Key / Access Checklist for App Data Gaps

_Verified live 2026-06-12. Maps each data gap from `docs/plans/civiclens-app-design.md` to the access it needs. Keys must be created manually (signups require human account creation); each is a ~2-minute task. New keys go in `.env` per `.env.example`._

## No action needed — existing keys cover these

| Gap | Key | Notes |
|---|---|---|
| FEC candidate totals (Phase 1) | `FEC_API_KEY` ✅ | `/candidate/{id}/totals` endpoint, same key |
| FEC Schedule A/B (Phase 3) | `FEC_API_KEY` ✅ | API for top-N; bulk CSVs from fec.gov need no key at all |
| Federal bills + House roll-call votes (Phase 2) | `CONGRESS_API_KEY` ✅ | House vote endpoints in beta since May 2025, cover 2023–present |
| OpenStates bill abstract/url/sponsors/votes (Phase 2) | `OPENSTATES_API_KEY` ✅ | Staging-layer change; raw VARIANT already loaded |
| Bill summaries, issue tagging, endorsement research | `ANTHROPIC_API_KEY` ✅ | |

## No key exists — public access

| Gap | Source | Access |
|---|---|---|
| Senate roll-call votes (Phase 2) | senate.gov roll-call XML | Public XML files, no auth. Congress.gov API has **no Senate vote endpoint** as of June 2026 — House only |
| Candidate bios | Wikipedia / Wikidata REST APIs; bioguide.congress.gov for federal | No key; set a descriptive `User-Agent` header per Wikimedia policy |

## Signup required (do these when the phase starts)

| Gap | Phase | Where to sign up | What you get |
|---|---|---|---|
| Issue positions / interest-group ratings | 4 | https://votesmart.org/share/api | Free key → `VOTESMART_API_KEY` (slot already in `.env.example`). Newer Swagger at https://api.paas.votesmart.io/api — confirm which surface the key targets |
| Donor industry codes (federal) | 3 | https://www.opensecrets.org/bulk-data/signup | Account approval (free, educational use), then manual CSV downloads — **no API**; their API was discontinued 2025-04-15 |

## Explicitly not needed

- **OpenSecrets API** — discontinued April 15, 2025. Do not budget for it; bulk CSVs are the only path.
- **FollowTheMoney** — merged into OpenSecrets; data no longer updated (frozen at 2024). Removed from the stack — state finance comes from per-state portals.
- **VoteSmart for federal votes** — Congress.gov + senate.gov cover voting records; VoteSmart is only for positions/ratings/bio.
