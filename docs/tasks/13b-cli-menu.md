# 13b – CLI menu and option flows
Status: done
Owner: agent
Depends on: 10, 11, 12, 13a

## Goal
The interactive menu with the original's six options plus 7 destination overview, in English,
built from task 13a's pieces and tested with scripted input and captured output.

## Context
- `docs/research.md` → "What we know (from the video)" (menu), Qs "What does option 4 let the user do?" and "How is search a specific flight implemented?"
- `docs/research.md` → "destinationer.py – Helper script", "How is destinationer.py reached"
- Task 13a's `Console`, prompts, renderer and pager; services from tasks 10, 11 and 12

## Acceptance criteria
- [x] `cli/menu.py`: a main loop with a **dispatch table** (dict of option → handler, not an if/elif chain), labels as the original's in English: 1 arrivals for an airport & date, 2 departures for an airport & date, 3 search a specific flight number (flight id + date), 4 OData query (presets for the chosen airport/date + "type your own filter"), 5 HeartBeat API health check, 6 demonstrate all endpoints automatically (stub until task 14), 7 destination overview, q quit
- [x] Options 1–4 show their flights through task 13a's renderer and pager. Option 5 prints each ping as it happens and then the summary
- [x] `cli/destinations.py`: `run_destination_overview(console, ...)` prompts in the original's order (airport, date, optional filter, then 1 arrivals / 2 departures / 3 both, re-prompting on anything else), renders city | country | count rows plus the unmatched cities, then returns to the menu
- [x] Every `ApiError` is caught at the menu level and shown as a friendly one-line message; the loop keeps running
- [x] Tests with scripted input and captured output: each option dispatches, invalid menu choices re-prompt (including the 1–3 choice in option 7), option 3 searches, option 4 runs a preset and a custom filter, option 5 prints pings and a summary, option 7 renders rows from a fake source, quit exits, an API error doesn't crash the loop

## Out of scope
Wiring real dependencies and `--offline`, and the full-auto demo itself (task 14).

## Notes
- From task 11: a ping that failed without a response has `status_code=None` and `latency_ms=0.0`. Print latency only for pings that got a response, so the screen never shows "0.0 ms" for a failure.
- From task 12: the overview is a free function, `destination_overview(source, lookup, airport, day, which, match=None)`, not a service object. Wire it with `functools.partial` (or pass `source` and `lookup` into `run_destination_overview`) rather than redesigning it. `Which("1"|"2"|"3")` maps the 1–3 answer directly.
- Done: `App(console, source, lookup, today, sleep, title)` is what task 14 must build. `run_menu(app)` is the entry point. Option 6 is a `# shortcut:` placeholder to replace with the demo.
- Done: an OK ping shows its message if it has one (e.g. offline mode's note); failures never show a time.
- **Corrected 2026-11-24:** there is no menu option 7. The overview is offered after options 1 and 2, built from the flights just listed (`summarise_destinations`). See PROGRESS.md, "Correction: no menu option 7".
