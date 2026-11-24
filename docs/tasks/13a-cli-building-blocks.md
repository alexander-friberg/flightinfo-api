# 13a – CLI building blocks: console, prompts, flight card, paging
Status: todo
Owner: agent
Depends on: 04

## Goal
The reusable pieces of the terminal UI, each testable on its own with scripted input and
captured output: input/output injection, the airport and date prompts, the original's flight
card, and paging. The menu and the option flows that use them are task 13b.

## Context
- `docs/research.md` → "What we know (from the video)" (prompts, paging), "Flight (as displayed)", Q "How are dates entered?", `_choose_airport()` fragment
- `docs/documentation.md` → DI table rows "User input" / "Output"

## Acceptance criteria
- [ ] `cli/io.py` (or similar): a small `Console` holding injected `read: Callable[[str], str]` and `write: Callable[[str], None]`
- [ ] `cli/prompts.py`: `choose_airport(console)` lists the 10 airports as `IATA – name` in the original's order, asks "Enter IATA code or city name (e.g. ARN or Visby)", uses `resolve_airport`, and re-prompts with "Unknown airport, try again." on bad input
- [ ] `choose_date(console, today: date)` accepts `YYYY-MM-DD`, `now`, `today`, `tomorrow`, `yesterday` and empty input (= today), case-insensitively, and re-prompts on anything else. `today` is passed in, never read from the system clock here
- [ ] `cli/render.py`: pure functions from `Flight` to the original's card layout (research.md "Flight (as displayed)"): `[N] → ID  |  Airline  (IATA)`, other airport as name + IATA, the queried airport with its name filled in from `AIRPORTS`, `Terminal : …    Gate: …`, times as `HH:MM UTC → HH:MM CET/CEST`, `–` for missing times and `N/A` for other missing values
- [ ] `cli/pager.py` (or in render): 50 flights per page, then `── Showing N/M ──  (K left)` and `[Enter] next page | [a] show all | [q] back to menu`
- [ ] Tests with scripted input and captured output: airport prompt (codes, city names, re-prompt), every date keyword and empty input plus a re-prompt, paging (Enter / `a` / `q`, the counter text, a list shorter than one page, an empty list), render output for one arrival and one departure fixture flight (snapshot-style string comparison, including a CET and a CEST time)

## Out of scope
The menu, the option flows, error handling at menu level (task 13b). Wiring real dependencies (task 14).

## Notes
