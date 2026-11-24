# 08 – Short-lived response cache
Status: done
Owner: agent
Depends on: 07

## Goal
Save quota by not re-fetching the same arrivals/departures within a short window, for example
when the user views arrivals again, or opens the destination overview right after viewing them.

## Context
- `docs/research.md` → "Quota"
- `CLAUDE.md` → composition over inheritance

## Acceptance criteria
- [x] `api/caching.py`: `CachingFlightSource(inner: FlightSource, ttl_s: float, clock: Callable[[], float])` that itself satisfies `FlightSource`
- [x] `arrivals` / `departures` are cached per `(airport, day)` until the TTL expires
- [x] `query` is cached per filter string. `health()` is **never** cached (a heartbeat must hit the API)
- [x] Errors are not cached
- [x] TTL ≤ 0 disables caching
- [x] Tests use `FakeFlightSource` + a fake clock: hit within TTL, miss after TTL, different keys, health never cached, errors not cached

## Out of scope
Persisting the cache to disk.

## Notes
- Default clock is `time.monotonic` (wall time can jump). Entries expire exactly at the TTL.
- Empty results are cached too. The cache never evicts (marked `# shortcut:` in the code).
