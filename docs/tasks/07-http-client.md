# 07 – FlightSource protocol and HTTP client
Status: todo
Owner: agent
Depends on: 03, 06

## Goal
The only code that talks to Swedavia. It sits behind a small Protocol so that services, cache,
offline mode and tests can all swap implementations.

## Context
- `docs/documentation.md` → "Planning: dependency injection" (the `FlightSource` sketch), testing strategy row "Client"
- `docs/api-reference.md`: paths, parameters, documented status codes, the query rate limit
- `docs/research.md` → "Endpoints (FlightInfo v2)" and the behaviour list under it, plus what task 05 found

## Acceptance criteria
- [ ] `api/protocols.py`: `FlightSource` Protocol with `arrivals(airport, day)`, `departures(airport, day)`, `query(odata_filter)`, `health()`
- [ ] `api/errors.py`: `ApiError` base class plus `AuthError` (401/403), `QuotaExceededError` (429, either the query rate limit of one call per 2 s or the monthly quota; the message covers both unless the response says which), `ApiUnavailableError` (5xx, timeout, connection error), `BadQueryError` (400 on query)
- [ ] `api/client.py`: `SwedaviaClient(settings, http: httpx.Client)`. The httpx client is injected; the class never creates its own
- [ ] Sends `Ocp-Apim-Subscription-Key` and `Accept: application/json` on every request; dates formatted `YYYY-MM-DD`; OData filter URL-encoded; `query` always sends an explicit `count` (a module constant, 1000) and no `continuationtoken`
- [ ] `204 No Content` from arrivals/departures returns an empty list, not an error
- [ ] `health()` calls `GET /heartBeat` (response body `{}`) and measures latency using an injected clock (`Callable[[], float]`, default `time.perf_counter`)
- [ ] Error messages never contain the key or the request headers
- [ ] Tests use `httpx.MockTransport` only: correct URL per method (including `count` on query), headers present, 204 → empty list, each status → right error, timeout → `ApiUnavailableError`, successful responses parsed via the fixtures, and the key absent from every error message
- [ ] `tests/fakes.py` gains `FakeFlightSource` (canned data plus a call counter) for later tasks

## Out of scope
Caching (08), offline data (09), retries.

## Notes
