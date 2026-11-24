# Swedavia Flight Board

A Python terminal app that shows real-time arrivals and departures for Sweden's 10 Swedavia
airports using the Swedavia FlightInfo API v2. It recreates an existing app and is built as a
school assignment and portfolio project. All code, comments, UI text and docs are in English.

## Where things are
- `docs/research.md`: what is known about the original app and the API, open questions, decisions.
  Read the sections a task links to before starting it.
- `docs/api-reference.md`: the official Swedavia FlightInfo v2 reference (endpoints, parameters,
  status codes, every response field). Use it instead of fetching the portal.
- `docs/documentation.md`: architecture, DI plan, testing strategy, CI decisions.
- `docs/tasks/NN-*.md`: the task queue. One task = one reviewable change = one commit by Alex.
- `docs/PROGRESS.md`: the work log. Append to it after every task.

## How to work
Work happens through `/next-task` (`.claude/skills/next-task/SKILL.md`). Do one task per run.
Never start a second task in the same run.

## Commands
- Sync environment: `uv sync`
- All checks: `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest`
- Run the app: `uv run python -m flightboard` (add `--offline` to use recorded data)
- Anything that needs the API key: `uv run --env-file .env <command>`

## Architecture rules
- Layers: `domain` ← `api` ← `services` ← `cli`. Inner layers never import outer ones. `domain` has no I/O.
- Inject every external dependency: HTTP transport, clock/sleep, input/output, data files, flight
  source. Only `src/flightboard/__main__.py` (the composition root) constructs real implementations.
- Services depend on the `FlightSource` Protocol, never on httpx or `SwedaviaClient` directly.
- Past `api/parsing.py`, flights are frozen dataclasses, not dicts. Ghost entries are filtered
  in the parser and nowhere else.
- Times are timezone-aware UTC internally. Convert to Europe/Stockholm only when rendering.
- Prefer composition (wrappers such as `CachingFlightSource`) over inheritance.
- Keep abstractions minimal. Don't add a Protocol unless it has at least two implementations
  (real + fake).
- Full type hints everywhere; `mypy --strict` must pass.

## Testing rules
- The default test run never touches the network. Use `httpx.MockTransport`, hand-written fakes
  in `tests/fakes.py` and JSON fixtures in `tests/fixtures/`.
- Prefer fakes over `unittest.mock`. Assert on results, not on call sequences.
- Tests that call the live API are marked `@pytest.mark.live` and excluded by default. Only run
  them when a task says so.
- Write the failing test before the implementation.

## API, quota and secrets
- The free-tier quota is small (assume 1 000 requests/month). Make live calls only when a task
  requires it, and never more than the number the task states.
- Never read, print or log `.env` or the API key. Load it only via `uv run --env-file .env`.
  Never put the key on a command line, in a fixture, in a log or in an error message.
- No curl or wget. Reach the Swedavia API only through project scripts. Read docs with WebFetch
  on the allowed domains.

## Git rules
- Alex writes and runs every commit. You never run `git commit` or `git push`.
- When a task is done, stage only that task's files, using explicit paths (`git add <paths>`).
- When you start, if the working tree has uncommitted changes from a previous task, stop and
  ask Alex to commit first.

## Style
- Python 3.12+. Line length 100; ruff rule sets are configured in `pyproject.toml`.
- Small modules with a single responsibility. Split any module that grows past ~200 lines.
- Plain `print`-based terminal output. No `rich` or other UI libraries.

### Comments
- Comments explain **why**, never **what**. Don't comment code that its names already explain.
- No change narration in code: no "Added…", "Updated…", "Fixed…", "New:", "Changed to…". History
  belongs in git and `docs/PROGRESS.md`.
- No mention of Claude, AI or generated code anywhere in source, tests, fixtures, commit
  messages or PR text.
- Short docstrings on public functions and classes are fine: one line, plus Args/Returns only
  when the types don't already say it.
- No commented-out code. A deliberate shortcut uses the form
  `# shortcut: <limit>, <when to upgrade>`; no other TODO-style comments.

### ponytail
The ponytail plugin (minimal-code mode) is enabled for this project. Where it and this file
disagree, this file wins. In particular, every acceptance criterion gets a test written first,
however small the change. During `/next-task`, the hand-off message is the whole reply: put what
you skipped or didn't check under its "Look closely at" section instead of a closing line.
