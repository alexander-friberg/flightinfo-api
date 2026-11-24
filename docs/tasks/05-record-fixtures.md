# 05 – Record fixtures and verify the API reference
Status: todo
Owner: agent (needs Alex's key in `.env`)
Depends on: 01, 03

## Goal
The official API reference is already in `docs/api-reference.md`. Save real responses as the
test fixtures every later task relies on, and check that the live API matches the reference.

## Before starting
**Alex:** put `SWEDAVIA_API_KEY=<key>` in `.env` (git-ignored). The agent never reads `.env`;
the script gets the key through `uv run --env-file .env`.

## Context
- `docs/api-reference.md`: the official reference for all four endpoints
- `docs/research.md` → "Endpoints (FlightInfo v2)", "Inconsistencies in the official docs", "Display field → API field", "Quota"

## Acceptance criteria
- [ ] `scripts/record_fixtures.py`: reads the key from the environment, sends it only in the `Ocp-Apim-Subscription-Key` header, and saves pretty-printed JSON to `tests/fixtures/`: `arrivals_ARN.json`, `departures_ARN.json`, `query_sample.json` (the search filter from research.md: `flightId` + `scheduled` in `YYMMDD`, **no `airport`**, explicit `count`) and `health.json` (expected `{}`). Leave at least 2 s between calls, because of the query rate limit
- [ ] The real responses are compared with `api-reference.md`. Any difference (a field that is missing or always empty, the outcome of each item in "Inconsistencies in the official docs" and the "Also verify" list: local vs UTC day, queries without `airport`, heartBeat and the quota) is recorded in `research.md`
- [ ] **At most 6 live API calls in total** for this task (the number used is logged in PROGRESS.md)
- [ ] The script scans its own output and fails if the key string appears in any saved file
- [ ] If the fixtures contain no ghost entry, a small hand-made `ghost_entries.json` is added for task 06
- [ ] The "Display field → API field" table in `research.md` is confirmed against the fixtures, including how city names are spelled (this matters for `city_country.json`)
- [ ] A `@pytest.mark.live` contract test that fetches arrivals and checks the top-level shape (excluded by default; not run in this task beyond one manual run, which counts toward the 6)

## Out of scope
The real HTTP client (task 07). This script is a one-off tool.

## Notes
