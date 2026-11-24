# 09 – Offline flight source
Status: done
Owner: agent
Depends on: 06, 07

## Goal
Let the app run without network access or an API key, using recorded data. This is useful for
the video, for demos and when the quota runs out. It's the same DI seam the tests use.

## Context
- `docs/research.md` → Q "What does run full-auto demo do?" (offline mode decision)

## Acceptance criteria
- [x] Sample data shipped inside the package (e.g. `src/flightboard/data/samples/`) so it works when installed. Copy it from the recorded fixtures; don't read from `tests/`
- [x] `api/offline.py`: `OfflineFlightSource` satisfying `FlightSource`. It serves the sample data for any airport/day (clearly labelled as sample data), returns a fixed healthy `HealthStatus`, and handles `query` for the filters search and the OData presets produce (`flightId`, optionally `airport`, `flightType`, `scheduled`) by matching the sample flights; any other filter gives a clear "not supported offline" result
- [x] Sample files loaded via `importlib.resources` behind an injectable loader
- [x] Tests: works with no network and no key; health is OK; the search filter finds a sample flight; an unsupported filter gives the documented result

## Out of scope
The `--offline` CLI flag (task 14).

## Notes
- Any airport/day gets the same recorded ARN sample (2026-11-24); flights keep `airport_iata="ARN"`, and `OfflineFlightSource.label` says what the data is (for task 14's header).
- Queries follow the same rule: `airport` and `scheduled` are validated (IATA shape; exact YYMMDD or YYYY-MM-DD) but don't narrow the sample, so searching today still finds the recorded flights. `flightId` and `flightType` do filter.
- "Not supported offline" = `BadQueryError` with a message listing what works (e.g. `flightStatus`, `or`, parentheses).
- Packaging verified: the built wheel contains `data/samples/*.json`, and an install outside the repo loads them.
