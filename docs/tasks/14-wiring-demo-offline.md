# 14 – Composition root, full-auto demo, --offline
Status: todo
Owner: agent
Depends on: 08, 09, 12, 13

## Goal
Wire the real objects together in one place, finish the full-auto demo, and add the `--offline`
flag. After this task the app is feature-complete.

## Context
- `docs/documentation.md` → "composition root"
- `docs/research.md` → Q "What does run full-auto demo do?"

## Acceptance criteria
- [ ] `__main__.py` is the only place that creates `httpx.Client`, `SwedaviaClient`, `CachingFlightSource`, `OfflineFlightSource`, the real clock/sleep and the real console. It uses `argparse` with `--offline`
- [ ] Online: config error (missing key) → clear message and exit code 2, not a traceback
- [ ] `--offline`: no key needed; the menu header clearly says it's offline sample data
- [ ] `cli/demo.py`: the full-auto demo runs arrivals, departures, a search, an OData query and a short heartbeat (e.g. 3 pings) against the default airport ARN and today's date without input, with headers between steps. It uses the same services as the menu, and a pause of at least 2 s between steps through the injected sleep (the query endpoint allows one call per 2 s)
- [ ] The `httpx.Client` is closed on exit (context manager)
- [ ] Tests: the demo runs end-to-end against `FakeFlightSource` with fake sleep, and the output contains every section; argument parsing for `--offline`
- [ ] Manual check by the agent: `uv run python -m flightboard --offline` starts and the demo option runs (no live calls)

## Out of scope
README and docs (task 15).

## Notes
