# 04 – Domain model and airports
Status: todo
Owner: agent
Depends on: 01

## Goal
The pure core of the app: typed flight objects and airport resolution. No I/O.

## Context
- `docs/research.md` → "Data model", "Airports", the `_choose_airport()` fragment, Q "Which aliases exist"
- `docs/documentation.md` → "Planning: architecture"
- `docs/api-reference.md` → `arrivalFlight` / `departureFlight` (every field is optional)

## Acceptance criteria
- [ ] `domain/models.py`: frozen dataclasses `Flight` and `FlightTimes` (scheduled / estimated / actual, all `datetime | None`, timezone-aware UTC); enums `Direction` (ARRIVAL, DEPARTURE) and `Scope` (DOMESTIC, INTERNATIONAL, SCHENGEN, UNKNOWN), matching the API's `diIndicator` values D/I/S
- [ ] `Flight` covers every displayed field: flight id, airline name and IATA code, the "other" airport's name and IATA code, status, terminal, gate, baggage belt (arrivals only), times, scope. Use `None` where the API may omit a value (per the API reference, that is every field). Field names may be adjusted in task 06 once real data is known
- [ ] A frozen `HealthStatus` dataclass (ok flag, HTTP status code, latency in ms, optional message) for the health endpoint
- [ ] `domain/airports.py`: `AIRPORTS` (10 IATA codes → names, in the original's order and naming from research.md "Airports") and `resolve_airport(raw: str) -> str | None`, which accepts IATA codes case-insensitively and aliases such as `arlanda`, `göteborg`/`goteborg`, `malmö`/`malmo`, `visby`, `kiruna`, `åre`/`are`/`östersund`/`ostersund`
- [ ] `to_local(dt: datetime) -> datetime` converting UTC to Europe/Stockholm via `zoneinfo`
- [ ] Parametrized tests: all codes, aliases with and without å/ä/ö, whitespace, unknown input → `None`, and a DST-boundary case for `to_local`

## Out of scope
Prompting the user (that's CLI, task 13). JSON parsing (task 06).

## Notes
