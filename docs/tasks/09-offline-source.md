# 09 – Offline flight source
Status: todo
Owner: agent
Depends on: 06, 07

## Goal
Let the app run without network access or an API key, using recorded data. This is useful for
the video, for demos and when the quota runs out. It's the same DI seam the tests use.

## Context
- `docs/research.md` → Q "What does run full-auto demo do?" (offline mode decision)

## Acceptance criteria
- [ ] Sample data shipped inside the package (e.g. `src/flightboard/data/samples/`) so it works when installed. Copy it from the recorded fixtures; don't read from `tests/`
- [ ] `api/offline.py`: `OfflineFlightSource` satisfying `FlightSource`. It serves the sample data for any airport/day (clearly labelled as sample data), returns a fixed healthy `HealthStatus`, and handles `query` for the filters search and the OData presets produce (`flightId`, optionally `airport`, `flightType`, `scheduled`) by matching the sample flights; any other filter gives a clear "not supported offline" result
- [ ] Sample files loaded via `importlib.resources` behind an injectable loader
- [ ] Tests: works with no network and no key; health is OK; the search filter finds a sample flight; an unsupported filter gives the documented result

## Out of scope
The `--offline` CLI flag (task 14).

## Notes
