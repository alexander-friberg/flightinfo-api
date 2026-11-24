# 14 – Composition root, full-auto demo, --offline
Status: done
Owner: agent
Depends on: 08, 09, 12, 13b

## Goal
Wire the real objects together in one place, finish the full-auto demo, and add the `--offline`
flag. After this task the app is feature-complete.

## Context
- `docs/documentation.md` → "composition root"
- `docs/research.md` → Q "What does run full-auto demo do?"

## Acceptance criteria
- [x] `__main__.py` is the only place that creates `httpx.Client`, `SwedaviaClient`, `CachingFlightSource`, `OfflineFlightSource`, the real clock/sleep and the real console. It uses `argparse` with `--offline`
- [x] Online: config error (missing key) → clear message and exit code 2, not a traceback
- [x] `--offline`: no key needed; the menu header clearly says it's offline sample data
- [x] `cli/demo.py`: the full-auto demo runs arrivals, departures, a search, an OData query and a short heartbeat (e.g. 3 pings) against the default airport ARN and today's date without input, with headers between steps. It uses the same services as the menu, and a pause of at least 2 s between steps through the injected sleep (the query endpoint allows one call per 2 s)
- [x] The `httpx.Client` is closed on exit (context manager)
- [x] Tests: the demo runs end-to-end against `FakeFlightSource` with fake sleep, and the output contains every section; argument parsing for `--offline`
- [x] Manual check by the agent: `uv run python -m flightboard --offline` starts and the demo option runs (no live calls)

## Out of scope
README and docs (task 15).

## Notes
- From 13b: build `App(console, source, lookup, today, sleep, title)` and call `run_menu(app)`. Replace option 6's placeholder (`_demo` in `cli/menu.py`) with the demo. Pass an offline `title` such as "Swedavia FlightInfo API v2 – OFFLINE sample data (ARN, 24 Nov 2026)".
- From 13b's review: offline mode's "not supported" message plus the live-API hint is about 400 characters. Shorten `SUPPORTED` in `api/offline.py` to one sentence (the offline title already explains the sample). Expected offline: the "Cancelled flights" preset always gives that message.
- From 13b's review: offline heartbeats show "OK, 0 ms (HTTP 200) – Offline mode: …" five times, and "0/0/0 ms". Consider a single ping offline, or no latency figures for offline health.
- Done: `App` moved to `cli/app.py` (menu imports the demo, the demo needs `App`: keeping it in `menu.py` would be a circular import). Ping and summary text moved to `cli/render.py`.
- Done: offline title is "Swedavia FlightInfo API v2 – Offline sample data: Stockholm Arlanda, 24 Nov 2026 (recorded), …"; `ping_count=1` offline. The single offline ping still shows "0 ms" with offline mode's note; accepted.
- Done: offline message is one sentence; the live hint keeps the operator list; together ≤ 280 characters.
- `main(argv, transport=None, sleep=time.sleep)`: the two extra parameters exist only for tests (a fake Swedavia, no waiting).
- The live online path was not run (0 live calls). It's covered by a test with a fake transport.
