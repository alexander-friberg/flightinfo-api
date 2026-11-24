# 10 – Flight services: list, search, OData
Status: todo
Owner: agent
Depends on: 07

## Goal
The features behind menu options 1–4, independent of both the terminal and HTTP.

## Context
- `docs/research.md` → menu options, Q "How is search a specific flight implemented?"

## Acceptance criteria
- [ ] `services/flights.py` with functions or a small class that takes a `FlightSource`
- [ ] Arrivals/departures for an airport and day, sorted by scheduled time
- [ ] Search by flight id and day, with **one** OData call: `flightId eq '<ID>' and scheduled eq '<YYMMDD>'`, plus `and airport eq '<IATA>'` only when an airport is given (optional; needed only if task 05 found the API requires it). No `flightType`, so arrivals and departures both match. The id is normalised first (upper case, spaces removed), so `sk 1415` finds `SK1415`. `scheduled` is the local Swedish date
- [ ] OData presets: a function that builds the preset filters for an airport and day (departures, arrivals, a single flight, by status), so the CLI only chooses between them
- [ ] OData passthrough: empty or whitespace-only filters are rejected before any API call; `BadQueryError` is surfaced with a helpful message
- [ ] Tests with `FakeFlightSource`: sorting, found / not found / multiple matches, search makes exactly one source call with the expected filter string, empty filter makes no source call, error propagation

## Out of scope
Formatting output (task 13).

## Notes
- From task 09: offline mode supports the search filter and the departures/arrivals/single-flight presets, but not "by status" (`flightStatus`), which raises `BadQueryError` "not supported offline". That's expected; the menu shows the message.
