# 13 – CLI: menu, prompts, rendering
Status: todo
Owner: agent
Depends on: 10, 11, 12

## Goal
The interactive terminal UI with the original's six options plus 7 destination overview, in
English, built so it can be tested with scripted input and captured output.

## Context
- `docs/research.md` → "What we know (from the video)" (menu, prompts, paging), "Flight (as displayed)", Qs "How are dates entered?" and "What does option 4 let the user do?", `_choose_airport()` fragment
- `docs/research.md` → "destinationer.py – Helper script", "How is destinationer.py reached"
- `docs/documentation.md` → DI table rows "User input" / "Output"

## Acceptance criteria
- [ ] `cli/io.py` (or similar): a small `Console` holding injected `read: Callable[[str], str]` and `write: Callable[[str], None]`
- [ ] `cli/prompts.py`: `choose_airport(console)` lists the 10 airports as `IATA – name` in the original's order, asks "Enter IATA code or city name (e.g. ARN or Visby)", uses `resolve_airport`, and re-prompts with "Unknown airport, try again." on bad input
- [ ] `choose_date(console, today: date)` accepts `YYYY-MM-DD`, `now`, `today`, `tomorrow`, `yesterday` and empty input (= today), case-insensitively, and re-prompts on anything else. `today` is passed in, never read from the system clock here
- [ ] `cli/render.py`: pure functions from `Flight` to the original's card layout (research.md "Flight (as displayed)"): `[N] → ID  |  Airline  (IATA)`, other airport as name + IATA, the queried airport with its name filled in from `AIRPORTS`, `Terminal : …    Gate: …`, times as `HH:MM UTC → HH:MM CET/CEST`, `–` for missing times and `N/A` for other missing values
- [ ] `cli/pager.py` (or in render/menu): 50 flights per page, then `── Showing N/M ──  (K left)` and `[Enter] next page | [a] show all | [q] back to menu`
- [ ] `cli/menu.py`: a main loop with a **dispatch table** (dict of option → handler, not an if/elif chain), labels as the original's in English: 1 arrivals for an airport & date, 2 departures for an airport & date, 3 search a specific flight number (flight id + date), 4 OData query (presets for the chosen airport/date + "type your own filter"), 5 HeartBeat API health check, 6 demonstrate all endpoints automatically (stub until task 14), 7 destination overview, q quit
- [ ] `cli/destinations.py`: `run_destination_overview(console, service)` prompts in the original's order (airport, date, optional filter, then 1 arrivals / 2 departures / 3 both, re-prompting on anything else), renders city | country | count rows plus the unmatched cities, then returns to the menu
- [ ] Every `ApiError` is caught at the menu level and shown as a friendly one-line message; the loop keeps running
- [ ] Tests with scripted input and captured output: each option dispatches, invalid choices re-prompt (including the 1–3 choice in option 7), option 7 renders rows from a fake service, quit exits, an API error doesn't crash the loop, every date keyword and empty input, paging (Enter / `a` / `q` and the counter text), option 4 runs a preset and a custom filter, render output for one arrival and one departure fixture flight (snapshot-style string comparison, including a CET and a CEST time)

## Out of scope
Wiring real dependencies and `--offline` (task 14).

## Notes
- From task 11: a ping that failed without a response has `status_code=None` and `latency_ms=0.0`. Print latency only for pings that got a response, so the screen never shows "0.0 ms" for a failure.
- From task 12: the overview is a free function, `destination_overview(source, lookup, airport, day, which, match=None)`, not a service object. Wire it with `functools.partial` (or pass `source` and `lookup` into `run_destination_overview`) rather than redesigning it. `Which("1"|"2"|"3")` maps the 1–3 answer directly.
