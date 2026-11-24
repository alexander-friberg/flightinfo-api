# 04 – Domain model and airports
Status: done
Owner: agent
Depends on: 01

## Goal
The pure core of the app: typed flight objects and airport resolution. No I/O.

## Context
- `docs/research.md` → "Data model", "Airports", the `_choose_airport()` fragment, Q "Which aliases exist"
- `docs/documentation.md` → "Planning: architecture"
- `docs/api-reference.md` → `arrivalFlight` / `departureFlight` (every field is optional)

## Acceptance criteria
- [x] `domain/models.py`: frozen dataclasses `Flight` and `FlightTimes` (scheduled / estimated / actual, all `datetime | None`, timezone-aware UTC); enums `Direction` (ARRIVAL, DEPARTURE) and `Scope` (DOMESTIC, INTERNATIONAL, SCHENGEN, UNKNOWN), matching the API's `diIndicator` values D/I/S
- [x] `Flight` covers every displayed field: flight id, airline name and IATA code, the "other" airport's name and IATA code, status, terminal, gate, baggage belt (arrivals only), times, scope. Use `None` where the API may omit a value (per the API reference, that is every field). Field names may be adjusted in task 06 once real data is known
- [x] A frozen `HealthStatus` dataclass (ok flag, HTTP status code, latency in ms, optional message) for the health endpoint
- [x] `domain/airports.py`: `AIRPORTS` (10 IATA codes → names, in the original's order and naming from research.md "Airports") and `resolve_airport(raw: str) -> str | None`, which accepts IATA codes case-insensitively and aliases such as `arlanda`, `göteborg`/`goteborg`, `malmö`/`malmo`, `visby`, `kiruna`, `åre`/`are`/`östersund`/`ostersund`
- [x] `to_local(dt: datetime) -> datetime` converting UTC to Europe/Stockholm via `zoneinfo`
- [x] Parametrized tests: all codes, aliases with and without å/ä/ö, whitespace, unknown input → `None`, and a DST-boundary case for `to_local`

## Out of scope
Prompting the user (that's CLI, task 13a). JSON parsing (task 06).

## Notes
- `Flight.airport_iata` was added: the Swedavia airport a record belongs to (the card fills in its name; airport-less search needs to show where a flight is).
- `Direction` values are the API's `flightType` codes (`A`/`D`); `Scope.from_indicator()` maps `diIndicator`.
- Plain "stockholm" is not an alias (ARN or BMA would be a guess).
- `tzdata` added as a runtime dependency (approved by Alex) so `zoneinfo` works on Windows.
