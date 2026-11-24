# 07 – FlightSource protocol and HTTP client
Status: done
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
- [x] `api/protocols.py`: `FlightSource` Protocol with `arrivals(airport, day)`, `departures(airport, day)`, `query(odata_filter)`, `health()`
- [x] `api/errors.py`: `ApiError` base class plus `AuthError` (401/403), `QuotaExceededError` (429, either the query rate limit of one call per 2 s or the monthly quota; the message covers both unless the response says which), `ApiUnavailableError` (5xx, timeout, connection error), `BadQueryError` (400 on query)
- [x] `api/client.py`: `SwedaviaClient(settings, http: httpx.Client)`. The httpx client is injected; the class never creates its own
- [x] Sends `Ocp-Apim-Subscription-Key` and `Accept: application/json` on every request; dates formatted `YYYY-MM-DD`; OData filter URL-encoded; `query` always sends an explicit `count` (a module constant, 1000) and no `continuationtoken`
- [x] `204 No Content` from arrivals/departures returns an empty list, not an error
- [x] `health()` calls `GET /heartBeat`, judges health by the HTTP status only (the docs say the body is `{}`, but it is really `"IsAlive"`; see `tests/fixtures/health.json`) and measures latency using an injected clock (`Callable[[], float]`, default `time.perf_counter`)
- [x] Error messages never contain the key or the request headers
- [x] Tests use `httpx.MockTransport` only: correct URL per method (including `count` on query), headers present, 204 → empty list, each status → right error, timeout → `ApiUnavailableError`, successful responses parsed via the fixtures, and the key absent from every error message
- [x] `tests/fakes.py` gains `FakeFlightSource` (canned data plus a call counter) for later tasks

## Out of scope
Caching (08), offline data (09), retries.

## Notes
- `health()` never raises for HTTP or network problems: it returns `HealthStatus(ok=False, …)`, with `status_code=None` when no response arrived.
- A 400 on arrivals/departures (and 404/304, any other unexpected status) is the base `ApiError`; `BadQueryError` is only for a 400 on a query.
- Redirects are never followed (`follow_redirects=False`), because httpx would carry the key header to another host.
- Outside the criteria: `tests/test_contract_live.py` now uses the app's `DEFAULT_BASE_URL` (deferred from task 05). `scripts/record_fixtures.py` keeps its own copy of the base URL on purpose; it's a one-off tool.
