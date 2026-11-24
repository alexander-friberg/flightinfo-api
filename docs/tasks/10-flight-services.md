# 10 – Flight services: list, search, OData
Status: done
Owner: agent
Depends on: 07

## Goal
The features behind menu options 1–4, independent of both the terminal and HTTP.

## Context
- `docs/research.md` → menu options, Q "How is search a specific flight implemented?"

## Acceptance criteria
- [x] `services/flights.py` with functions or a small class that takes a `FlightSource`
- [x] Arrivals/departures for an airport and day, sorted by scheduled time
- [x] Search by flight id and day, with **one** OData call: `flightId eq '<ID>' and scheduled eq '<YYMMDD>'`, plus `and airport eq '<IATA>'` only when an airport is given (optional; needed only if task 05 found the API requires it). No `flightType`, so arrivals and departures both match. The id is normalised first (upper case, spaces removed), so `sk 1415` finds `SK1415`. `scheduled` is the local Swedish date
- [x] OData presets: a function that builds the preset filters for an airport and day (departures, arrivals, a single flight, by status), so the CLI only chooses between them
- [x] OData passthrough: empty or whitespace-only filters are rejected before any API call; `BadQueryError` is surfaced with a helpful message
- [x] Tests with `FakeFlightSource`: sorting, found / not found / multiple matches, search makes exactly one source call with the expected filter string, empty filter makes no source call, error propagation

## Out of scope
Formatting output (task 13).

## Notes
- **Alex (2026-11-24): "Deleted" (`DEL`) flights are listed as-is**, with no filtering, and their status text is shown unchanged.
- From task 09: offline mode supports the search filter and the departures/arrivals/single-flight presets, but not "by status" (`flightStatus`), which raises `BadQueryError` "not supported offline". That's expected; the menu shows the message.
- The "by status" preset is fixed to cancelled flights (`flightStatus eq 'CAN'`, a code seen in the task-05 data), so it needs no extra input. Only the single-flight preset asks for a flight id (`ODataPreset.needs_flight_id`).
- Flight ids (letters and digits only after normalising) and airports (three letters) are validated before they go into a filter or URL, so typed quotes can't change a query. Bad input raises `BadQueryError` without an API call.
- `run_query` appends a hint worded for the *live* API, so it doesn't contradict offline mode's own "not supported offline" message.
