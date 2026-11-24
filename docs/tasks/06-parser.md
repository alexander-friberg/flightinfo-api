# 06 – Parser and ghost-entry validation
Status: done
Owner: agent
Depends on: 04, 05

## Goal
Turn raw API JSON into domain objects at the edge of the system, so nothing further in sees
dicts, ghost entries or half-missing data.

## Context
- `docs/research.md` → `_is_valid_flight()` fragment, "Display field → API field", "Observations from these fragments"
- `docs/api-reference.md` → response bodies, especially the query's `flightsResponse`
- Fixtures in `tests/fixtures/`

## Acceptance criteria
- [x] `api/parsing.py`: `is_valid_flight(raw: Mapping[str, object]) -> bool` keeps the original's semantics (valid if it has an id OR an other-airport OR a scheduled time)
- [x] `parse_flights(payload, direction: Direction) -> list[Flight]` parses a full arrivals/departures response, skipping ghost entries
- [x] `parse_query(payload) -> list[Flight]` parses a query response: each item wraps an `arrival` or a `departure`, and the `Direction` comes from which key is present
- [x] Missing optional fields become `None`, never a crash. A malformed timestamp is treated as missing, not raised
- [x] Timestamps parsed into timezone-aware UTC `datetime`s
- [x] `diIndicator` D/I/S mapped to `Scope`, with missing or unknown values → `Scope.UNKNOWN`
- [x] If the real data showed the task 04 field names were wrong, `Flight` is adjusted here and the change noted in PROGRESS.md
- [x] Tests: both real fixtures parse fully; flight count equals the raw count minus ghosts; one known flight is checked field by field; ghost entries removed; missing-field and bad-timestamp cases; the query fixture parses as well

## Out of scope
HTTP (task 07).

## Notes
- Criterion 22: the real data fit task 04's `Flight` field names; no change was needed.
- `is_valid_flight` keeps the original's quirk (`arrivalTime or departureTime`), pinned by a test.
