# Documentation – Swedavia Flight Board (recreation)

> All documentation and the video are in English, as the assignment requires.
> Sections marked *(fill in)* are written during and after implementation.

## Purpose
Recreate a terminal application that shows real-time arrivals and departures for Sweden's ten Swedavia airports using the Swedavia FlightInfo API v2. The original application is known only from a video and a few code fragments, so part of the work is reverse engineering its behaviour.

The recreation is also a **portfolio project**. Beyond matching the original's features, it aims to show:
- a modular, layered structure
- dependency injection, so all logic is testable without the live API
- an automated test suite
- secure handling of secrets
- a small, useful CI pipeline

### Deliverables
- [ ] Working application in a public GitHub repository
- [ ] `README.md` (what it is, how to install, configure and run it, how to run the tests)
- [ ] This documentation (phases 1–4 + conclusion)
- [ ] Video, at least 4 minutes, screen recording with clear audio, covering purpose, phases, problems/solutions and examples

---

## Phase 1: Research (pre-study)

### Information gathering
- **Swedavia developer portal**: API policies, subscription, quota and the FlightInfo v2 operation pages for all four endpoints (copied into `docs/api-reference.md`).
- **Video of the original application**: menu structure, features, the airport and date prompts, the flight card layout and paging (described in `research.md` → "What we know (from the video)").
- **Known source code fragments**: `_choose_airport()` and `_is_valid_flight()`.
- **Python documentation**: `dataclasses`, `typing.Protocol`, `zoneinfo`, `json`.
- **Library documentation**: `httpx` (especially `MockTransport`), `pytest`.

All findings about the original application are compiled in `research.md`, including the open questions the video doesn't answer and how each one was resolved. Anything the video doesn't cover is recreated to the best of my ability and marked as a deliberate decision.

### Choice of tools and techniques
| Area | Choice | Why |
|---|---|---|
| Language | Python 3.12+ | Same as the original |
| Project & dependencies | `uv` (`pyproject.toml` + `uv.lock`) | One fast tool for venv, dependencies and running; `--env-file` loads secrets |
| HTTP | `httpx` | Its transport can be swapped for a fake in tests |
| Data model | `dataclasses` (frozen) + enums | Typed, immutable flight objects instead of loose dicts |
| Abstractions | `typing.Protocol` | Structural interfaces; minimal ceremony |
| Testing | `pytest` | Fixtures, parametrization |
| Quality | `ruff`, `mypy` | Lint, formatting, type checking |
| CI | GitHub Actions | See *CI considerations* below |
| AI assistance | Claude Code with the ponytail plugin (minimal-code mode), in an agentic workflow | Implements tasks from written specs; I review and commit every change. See *Planning: development workflow* |
| Other | Manual research and documentation | |

### Planning: architecture
The original keeps HTTP calls, parsing, business logic and UI in one file. The recreation separates them into layers that only depend "inwards":

```
cli  ──►  services  ──►  domain
              │
              ▼
     api (implements FlightSource)
```

- **domain**: the `Flight` model, enums (direction, D/I) and pure functions. No I/O at all.
- **api**: talks to Swedavia and turns JSON into domain objects. Ghost-entry validation lives here.
- **services**: the features (list arrivals, search, destination statistics, heartbeat). Depend on a `FlightSource` protocol, never on `httpx` directly.
- **cli**: menu, input and rendering. Depends on services, and receives input/output functions instead of calling `input()`/`print()` directly.
- **composition root** (`__main__.py`): the only place where real objects are created and wired together.

### Planned file structure
```
swedavia-flightboard/
├── pyproject.toml
├── uv.lock
├── README.md
├── CLAUDE.md                  # always-on rules for the coding agent
├── .env.example               # SWEDAVIA_API_KEY=  (the real .env is git-ignored)
├── .gitignore
├── .github/workflows/ci.yml
├── .claude/
│   ├── settings.json          # agent permissions + hooks
│   ├── hooks/                 # format.sh (after edits), checks.sh (before finishing)
│   ├── skills/next-task/      # the work loop, run as /next-task
│   └── agents/reviewer.md     # read-only reviewer subagent
├── docs/
│   ├── research.md
│   ├── api-reference.md       # official FlightInfo v2 reference, copied from the portal
│   ├── documentation.md
│   ├── PROGRESS.md            # work log, raw material for phases 2–4
│   └── tasks/                 # 01–15, one reviewable change each
├── scripts/
│   ├── record_fixtures.py     # one-off: real API responses -> tests/fixtures
│   └── build_city_country.py  # Excel statistics -> city_country.json (not run by the app)
├── src/flightboard/
│   ├── __main__.py            # composition root: config, wiring, --offline, start menu
│   ├── config.py              # reads env vars, fails clearly if key is missing, masks key
│   ├── domain/
│   │   ├── models.py          # Flight, FlightTimes, HealthStatus, Direction, Scope (D/I/S)
│   │   └── airports.py        # AIRPORTS, aliases, resolve_airport(), to_local()
│   ├── api/
│   │   ├── protocols.py       # FlightSource protocol
│   │   ├── client.py          # SwedaviaClient (httpx), headers, errors
│   │   ├── caching.py         # CachingFlightSource (wraps any FlightSource)
│   │   ├── offline.py         # OfflineFlightSource (recorded sample data)
│   │   ├── parsing.py         # JSON -> Flight, is_valid_flight()
│   │   └── errors.py          # AuthError, QuotaExceededError, ApiUnavailableError, BadQueryError
│   ├── services/
│   │   ├── flights.py         # arrivals, departures, search, OData
│   │   ├── destinations.py    # unique cities/countries + counts, filters
│   │   └── health.py          # heartbeat
│   ├── data/
│   │   ├── city_country.json
│   │   ├── samples/           # offline sample data
│   │   └── lookup.py          # CityCountryLookup
│   └── cli/
│       ├── io.py              # Console with injected read/write
│       ├── menu.py            # main loop, dispatch table instead of if/elif chain
│       ├── prompts.py         # choose_airport() etc.
│       ├── render.py          # Flight -> formatted text
│       ├── destinations.py    # destination overview, offered after options 1 and 2
│       └── demo.py            # full-auto demo
└── tests/
    ├── fixtures/              # recorded, sanitised real API responses (JSON)
    ├── fakes.py               # FakeFlightSource, FakeClock, scripted input
    ├── test_parsing.py
    ├── test_airports.py
    ├── test_client.py
    ├── test_flights_service.py
    ├── test_destinations.py
    ├── test_health.py
    └── test_cli.py
```

### Planning: dependency injection
Every external dependency is passed in, not reached for. These are the seams:

| Dependency | Real implementation | Test replacement |
|---|---|---|
| Flight data | `SwedaviaClient` | `FakeFlightSource` returning fixtures |
| HTTP transport | `httpx.Client` | `httpx.MockTransport` with a handler function |
| Time ("today", latency, sleep) | system clock | `FakeClock` the test controls |
| User input | `input` | iterator of scripted answers |
| Output | `print` | function that appends to a list |
| City → country | JSON file | small in-memory dict |

The central abstraction is small on purpose, along the lines of:

```python
class FlightSource(Protocol):
    def arrivals(self, airport: str, day: date) -> list[Flight]: ...
    def departures(self, airport: str, day: date) -> list[Flight]: ...
    def query(self, odata_filter: str) -> list[Flight]: ...
    def health(self) -> HealthStatus: ...
```

**Fakes over mocks.** Hand-written fakes (classes that behave like the real thing with canned data) are preferred over `unittest.mock`, because tests then check *results* rather than *which methods were called*, and they don't break when internals are refactored. `MagicMock` is reserved for the few places where the interaction itself is what's being tested.

A side benefit: the same seam lets the app run in **offline mode** (`--offline`) on recorded fixtures. That is useful for the video, for demos without an API key, and when the monthly quota runs out.

### Planning: testing strategy
| Level | What is tested | How |
|---|---|---|
| Unit: domain | airport/alias resolution, time conversion UTC → Europe/Stockholm, D/I logic | plain pytest, parametrized |
| Data | shipped `city_country.json` has the counts the build script reports, no empty values or placeholder/subtotal rows, known cities map correctly; build script reproduces it | load the real file (no network) |
| Unit: parsing | real fixture → correct `Flight`, ghost entries removed, missing fields don't crash | recorded JSON fixtures |
| Client | correct URL and date format, subscription-key header sent, 401/429/5xx/timeout → right error type | `httpx.MockTransport` |
| Services | search finds/doesn't find, destination counts and filters, unknown city → "Unknown" | `FakeFlightSource` |
| Heartbeat | N pings, min/avg/max latency, partial failure | recording fake sleep + fake source with scripted results (no real sleeping) |
| CLI | menu dispatch, invalid input re-prompts, quit works | scripted input + captured output |
| Contract (optional, manual) | the real API still returns what the parser expects | marked `@pytest.mark.live`, **excluded by default** |

Rule: **the default test run never touches the network.** That keeps it fast, deterministic, free of quota cost and runnable in CI without secrets.

### Planning: development workflow
The project is built with an **agentic workflow** in Claude Code. Instead of prompting the agent
step by step, the work is described in files in the repository:

| File | Role |
|---|---|
| `CLAUDE.md` | Always-on rules: architecture, testing, secrets/quota, git, style. The comment rules ban change narration, comments that restate the code, and any AI attribution, so the code reads as normal hand-maintained code |
| ponytail plugin | Enabled in `.claude/settings.json`. Pushes the agent to write only what a task needs and to reuse what exists. Where it disagrees with `CLAUDE.md` (for example, it only requires tests for non-trivial logic), `CLAUDE.md` wins |
| `docs/tasks/NN-*.md` | Task queue. Each task has a goal, context links, dependencies and **acceptance criteria that can be checked by running commands** |
| `.claude/skills/next-task/SKILL.md` | The work loop, run as `/next-task`: pick the next ready task → tests first → implement → review → log → stage |
| `.claude/agents/reviewer.md` | A read-only reviewer subagent that checks each change against the rules, so the agent doesn't grade its own work |
| `.claude/hooks/` | Deterministic guardrails: format after every edit; block finishing while lint, types or tests fail |
| `.claude/settings.json` | Enables ponytail; no attribution lines in commits/PRs. Permissions: no reading `.env`, no curl/wget, no `git commit`/`git push`; adding dependencies needs my approval |
| `docs/PROGRESS.md` | The agent's work log: decisions, problems and solutions per task |

**I stay in control of the repository.** The agent stages each finished task and hands over a
summary and an explanation of the code. I review `git diff --staged`, then write and run every
commit myself. One task is one commit.

The API key never passes through the agent: it lives in a git-ignored `.env` that the agent is
not allowed to read, and scripts get it via `uv run --env-file .env`.

### Planning: work order
The work is split into 15 small tasks in `docs/tasks/`, each one a reviewable commit:

| # | Task | Depends on |
|---|---|---|
| 01 | Project skeleton and tooling | – |
| 02 | CI workflow | 01 |
| 03 | Configuration and secrets | 01 |
| 04 | Domain model and airports | 01 |
| 05 | Record fixtures and verify the API reference (≤ 6 live calls) | 01, 03 |
| 06 | Parser and ghost-entry validation | 04, 05 |
| 07 | FlightSource protocol and HTTP client | 03, 06 |
| 08 | Short-lived response cache | 07 |
| 09 | Offline flight source | 06, 07 |
| 10 | Flight services: list, search, OData | 07 |
| 11 | Health check heartbeat | 07 |
| 12 | Destination statistics | 04, 07 |
| 13a | CLI building blocks: console, prompts, flight card, paging | 04 |
| 13b | CLI menu and option flows | 10, 11, 12, 13a |
| 14 | Composition root, full-auto demo, `--offline` | 08, 09, 12, 13b |
| 15 | README, documentation draft, video outline | 14 |

### CI considerations
**Is CI relevant for a project this small?** Yes, in a limited form.

Arguments for:
- It proves the tests actually run and pass on a clean machine, not just "on my laptop". That ties directly into the Phase 3 problem "works locally but not in the final version".
- It catches the cheap mistakes (lint, type errors, a forgotten import) on every push.
- The cost is low: one workflow file of roughly 30 lines.
- For a portfolio aimed at DevOps/SRE/Platform roles, a green pipeline and a status badge in the README are expected signals.
- CI only makes sense *because* of the DI design. Without network-free tests there would be nothing meaningful to run.

Arguments against / where to stop:
- There is no deployment target, so **CD is not relevant**. Publishing to PyPI, Docker images and release automation would be scope creep and would look like CI for show.
- Live API calls in CI would waste quota and require the key as a CI secret, so they're excluded.

**Decision: a single CI workflow** on push and pull request:
1. Install the project with `uv sync --locked`
2. `ruff check` and `ruff format --check`
3. `mypy`
4. `pytest` with a coverage report
5. Python version matrix: 3.12 and 3.13 (cheap and shows awareness of compatibility)
6. **Secret scanning** with gitleaks over the full history. This is especially relevant because the original application had its API key in plaintext.

The CI checks are the same ones the local Stop hook runs, so "green locally" and "green in CI" mean the same thing.

Not now, possible later:
- **Dependabot** for dependency updates.
- **Scheduled contract test** (weekly, key stored as a GitHub secret) that alerts if Swedavia changes the response format. It costs about 4 requests per month.

### Problems and solutions (research phase)
- **Problem:** The Swedavia portal was down so planning had to be around that in mind.
  **Solution:** Decide on swappable behaviour and implement dependency injection.
- **Problem:** The original source code was not available, only a video and some functions.
  **Solution:** Documented everything observable in `research.md`, listed open questions explicitly and resolved each with a documented hypothesis and decision.
- **Problem:** The heartbeat in the health check is mentioned but never shown.
  **Solution:** Designed a quota-friendly repeated ping with latency statistics, see `research.md`.
- **Problem:** The API documentation is spread across separate portal pages, and sources disagree on the free-tier quota (1 000 vs 10 000 requests/month).
  **Solution:** Collected the official reference for all four endpoints in one file (`api-reference.md`), noting where the docs contradict themselves. For the quota, assume the lower limit and design so that development and testing use recorded fixtures instead of the live API.
- **Problem:** The original's structure (one file, hard-wired I/O) can't be tested.
  **Solution:** Planned a layered architecture with dependency injection before writing any code.
- **Problem:** The API key was in plaintext in the original source.
  **Solution:** Environment variable + git-ignored `.env`, with `.env.example` committed instead. Gitleaks in CI catches it if a key is ever committed by mistake.
- **Problem:** Using an AI coding agent risks code I don't understand, changes I didn't approve, and wasted API quota.
  **Solution:** Small tasks with testable acceptance criteria, a separate reviewer subagent, hooks that block unfinished work, permissions that deny secrets and commits, and a written explanation with every handoff. I review and commit every change myself.

---

## Phase 2: Implementation

### How the work started
I created the repository with the research, the task queue and the Claude Code setup (`CLAUDE.md`, `.claude/`) as the first commit, so the rules and the plan existed before any code. From then on every change went through the same loop: the agent took the next task from `docs/tasks/`, wrote tests first, implemented, had the reviewer subagent check it, logged it in `PROGRESS.md` and staged it. I read the staged diff and the agent's explanation, and committed it myself. The project ended up as 20 commits, one per task plus a few separate fixes. 

The first two tasks were pure setup:
- **Task 01, the skeleton:** a `uv` project with a `src/` layout, an empty package for each layer, and ruff, mypy (strict) and pytest configured. From this point the Stop hook ran the full check on every turn, so nothing unfinished could be handed over.
- **Task 02, CI:** a GitHub Actions workflow with two jobs. One runs the same checks on Python 3.12 and 3.13; the other scans the whole git history for secrets with gitleaks. **The first CI run failed.** The `setup-uv` action has no `v10` tag, only full versions. I had misread its README, which pins a commit with a `# v10.4.0` comment. Pinning that exact commit made CI green. The secret scan passed on that first run, so the repository started clean.

### Project structure
The final structure follows the plan in Phase 1, with these differences:

| Difference | Why |
|---|---|
| `cli/app.py` holds `App`, the bundle of everything the menu needs | The menu calls the demo and the demo needs `App`; keeping `App` in `menu.py` would have been a circular import |
| `cli/pager.py` is its own module | Paging (50 flights per page, Enter / `a` / `q`) is used by both the flight lists and the destination table |
| `cli/destinations.py` is an offer after menu options 1 and 2, not its own menu option | The original's menu has six options; see "Problems and solutions" below |
| `data/samples/` holds a copy of the recorded responses | Offline mode must work after installing the package, without the `tests/` folder |
| Many small test files (one per module) instead of a few large ones | Each test file matches one module, so a failing test points straight at the code |
| No `FakeClock` class; tests pass small functions instead (`lambda: 0.0`, `sleeps.append`) | Injecting a plain function was enough everywhere, so a class would have been extra code |
| `.gitleaksignore` | One known false positive in the history (see below) |

### What was built first
I built from the inside out:
1. **The domain (task 04):** the `Flight` model and the airport list. It has no I/O at all, so it's tested with plain values.
2. **Real data (task 05):** one small script recorded real responses from the API as test fixtures. This used 6 live calls, planned in advance.
3. **The parser (task 06):** turns that real JSON into `Flight` objects.
4. Only then the HTTP client (07), and after that everything that uses it.

This order made testing easy. Every layer was tested against the layer below it, which already existed and worked. The parser was tested on *real* recorded data, not on what I guessed the API would return. By the time the HTTP client existed, the hard part (turning messy JSON into clean objects) was already proven, so the client tests only had to check URLs, headers and error codes. They do that against a fake Swedavia (`httpx.MockTransport`), so the 521 tests run in about a second and never touch the network.

### How the features were developed
All features depend on one small interface, `FlightSource` (arrivals, departures, query, health). The real client, the cache, the offline source and the test fake are four implementations of it. That's why offline mode and the tests needed no special code paths in the features themselves.

#### Arrivals and departures (options 1 and 2)
The service asks the source for one airport and day, then sorts by scheduled time. The menu shows the flights as cards with the original's layout and spacing, copied from the video, 50 per page. Times are shown as `16:25 UTC → 17:25 CET`, converted with `zoneinfo`, including summer time (CEST). I made one deliberate change to the original's card: both airports are shown as `Name (IATA)`, so the queried airport's name is filled in where the original left it blank. Flights with status "Deleted" (about one in five) are listed as they come, which was my decision since they're real records.

#### Search (option 3)
One OData query finds a flight number on a date at *every* Swedavia airport: `flightId eq 'SK1415' and scheduled eq '261124'`. That's one API call instead of two, and recording real data (task 05) proved the API accepts a query without an airport. The flight number is normalised (`sk 1415` finds `SK1415`) and must be letters and digits only, so a typed quote can't change the query (the same idea as SQL injection).

#### OData query (option 4)
The user picks an airport and a date, then one of four ready-made queries:
- departures
- arrivals
- one flight
- cancelled flights

The fifth choice is to type their own filter. If Swedavia rejects a typed filter, the message adds a short hint with the supported fields and an example.

#### HeartBeat (option 5)
The original only mentions a "heartbeat" health check, so I recreated it like the `ping` command: five calls to `/heartBeat`, 2 s apart, each printed as it happens, then a summary (successes, failures, min/avg/max latency). The waiting is an injected `sleep` function, so the tests check the exact rhythm without waiting.

The API documentation says `/heartBeat` returns `{}`, but the real response is `"IsAlive"`. So health is judged by the HTTP status code only.

#### Destination overview (the original's `destinationer.py`)
After options 1 and 2 list their flights, the app asks whether to show a destination overview. The overview lists every city with its country and number of flights, sorted by count. It has an optional filter on country or city, and lists the cities missing from the statistics file. It's counted from the flights already listed, so it costs no extra API call.
- **Where the countries come from:** a build script turns Swedavia's official 2025 statistics (Excel) into `city_country.json`, with 345 cities in 67 countries. Rerunning it gives an identical file, so next year's statistics are one command away.
- **Matching names:** city names from the API are matched ignoring case and å/ä/ö. Airport codes are stripped (`London LHR` → `London`), and a small alias table covers known spelling differences (`Munich` → `München`).

#### Full-auto demo (option 6)
The demo runs five headed steps with no input against Arlanda today:
1. arrivals
2. departures
3. a search for the first real departure
4. an OData query
5. three heartbeat pings

It uses exactly the same services as the menu. It pauses 2.5 s between steps because the query endpoint only allows one call per 2 s, and steps 3 and 4 are both queries. A failing step prints its error and the demo continues.

#### Offline mode (`--offline`)
`uv run python -m flightboard --offline` runs the whole app on the recorded Arlanda day, with no key and no network. The header says it's sample data. Offline mode is just another `FlightSource`; the only place that knows about it is `__main__.py`, which builds either the real stack or the offline one. It's useful for the video and when the monthly quota runs out.

#### Configuration and secrets
The API key is read from an environment variable that `uv run --env-file .env` loads from a git-ignored `.env`:
- If the key is missing, the app prints one line explaining what to do and exits with code 2, before any network object exists.
- The key is masked as `***` whenever the settings are printed.
- The key is sent only in a request header, never in the URL.
- Error messages are scrubbed of it.
- HTTP redirects are never followed.

### Problems and solutions
- **Problem:** The API documentation didn't match the real API. The heartbeat returns `"IsAlive"` instead of `{}`, and `DEL` turned out to mean "Deleted", not "delayed" as I first assumed.
  **Solution:** Before writing the client, I recorded real responses (6 live calls, planned in advance) and compared them with the documentation. Every difference is listed in `research.md`, and the code follows the real behaviour. The client was then built and tested against real data, not the documentation.
- **Problem:** The API leaves out missing fields instead of sending them empty, and the original's code shows it can send "ghost" entries with no flight number, airport or time.
  **Solution:** One parser at the edge of the program turns raw JSON into `Flight` objects:
  - Every missing, empty or wrongly typed value becomes "missing", and a broken timestamp counts as missing rather than crashing.
  - Ghost entries are removed with the original's own rule.
  
  Nothing past the parser ever sees raw JSON.
- **Problem:** Time zones. The API gives UTC, users want Swedish time, and summer time makes this easy to get wrong.
  **Solution:** All times are stored as UTC and converted to `Europe/Stockholm` only when shown. Times without a time zone are refused, because Python would silently treat them as the computer's own local time. Tests cover both daylight-saving switches. One of those tests failed even though the conversion was right: for the repeated hour in October, Python deliberately treats the same moment in two time zones as *unequal* (PEP 495). The test now compares the actual instants.
- **Problem:** CI failed twice for reasons unrelated to my code.
  - The `setup-uv@v10` tag doesn't exist (see "How the work started").
  - gitleaks flagged a *made-up* API key in a test as a real secret. Because the scan covers the whole history, changing the test didn't help.
  
  **Solution:**
  - Pin the exact commit of `setup-uv`.
  - For gitleaks, ignore that one finding by its exact fingerprint (commit + file + rule + line) in `.gitleaksignore`, so every other secret is still caught. Test keys are now obviously fake (`"fake-key"`).
- **Problem:** The full-history secret scan I had planned didn't scan the full history. gitleaks-action only scans the newly pushed commits, whatever `fetch-depth` is set to.
  **Solution:** The reviewer questioned it, and reading the action's source code confirmed it. CI now runs the gitleaks program itself, pinned and checksum-verified, with `--log-opts="--all"`.
- **Problem:** A security hole the tests didn't cover. When `httpx` follows a redirect to another host, it keeps custom headers, and the Swedavia key is sent in a custom header.
  **Solution:** Redirects are never followed. A test builds a client *with* redirects switched on and checks that the key only ever reaches Swedavia.
- **Problem:** City names from the API don't match the statistics file one-to-one: `London LHR`, `Addis Abeba` vs `Addis Ababa`, `Munich` vs `München`. My own first search missed `München` because of the ü.
  **Solution:** City names are matched with case and accents ignored, airport codes are stripped, and there's an alias table for the spelling differences. A test checks that every city in the recorded data resolves, except the API's own "Unknown".
- **Problem:** A misunderstanding about the original's menu. I had added a seventh option, "Destination overview", but the original has exactly six.
  **Solution:** The overview became part of options 1 and 2, built from the flights already fetched, and option 7 was removed. The decision and how the misunderstanding happened are recorded in `research.md` and `PROGRESS.md`. 
- **Problem:** Some tests couldn't fail. One checked "something came back" instead of the right value. Another computed its expected result with the function it was testing, and one "immutability" test would still pass if the object stopped being immutable.
  **Solution:** For each guarantee the reviewer questioned, the fix was checked by removing the code it protects and confirming the test then fails. The client closing on exit, the redirect block and the cache's copies were all checked this way.

---

## Phase 3: Completion & improvement

### Finishing the project
The last part of the work joined the pieces into a program:
- **The terminal UI:** I split it into two tasks so each commit stayed small enough to review properly.
  - Task 13a built the building blocks: a console with injected input and output, the airport and date prompts, the flight card and paging.
  - Task 13b built the menu and the option flows on top of them.
- **The composition root (task 14):** `__main__.py` is the one file that creates the real objects (the HTTP client, the Swedavia client, the cache, the offline source, the clock and the console) and passes them in. The same task added the full-auto demo and the `--offline` flag. After it, `python -m flightboard` started the real application.
- **One correction after that:** the recreation had a seventh menu option, "Destination overview", that the original doesn't have. I moved the overview into options 1 and 2 and removed the extra option, as its own commit, so the menu matches the original's six options.

At that point every feature of the original existed, and the recreation also had:
- offline mode
- clear error handling
- the tests and the CI pipeline

### Testing the whole solution
**Automated tests:**
- **Size and speed:** 521 tests in 25 test files run in about two seconds and never touch the network. The only line they don't execute is the `if __name__ == "__main__":` line that starts the program, which a test runs in a separate process where coverage can't see it. That gives 99 % line coverage (843 statements).
- **The test double each layer uses:**

  | Layer | Test double |
  |---|---|
  | Domain (flight model, airports, time zones) | plain values, no fakes needed |
  | Parser | the real API responses recorded in task 05 |
  | HTTP client | a fake Swedavia built on `httpx.MockTransport` that plays any status code, timeout or malformed body |
  | Services, cache, heartbeat | a hand-written `FakeFlightSource` and a recording `sleep`, so nothing really waits |
  | Menu and prompts | a scripted console that answers from a list and records every line printed, so a whole session is tested as text |
- **A live contract test** checks that the real API still answers in the shape the parser expects. It's excluded by default because it costs quota, and is run on purpose with `pytest -m live`.

**CI:** every push runs the same checks as my local hooks (ruff, formatting, strict mypy, the test suite) on Python 3.12 and 3.13, plus a gitleaks scan of the whole git history. CI has been green on every push since the two CI fixes described in Phase 2.

**Testing the tests:** for the most important guarantees, I removed the code that provides the guarantee and confirmed the test then fails:
- the HTTP client being closed when the program ends
- redirects never being followed (so the API key can't leak to another host)
- the cache keeping its own copy of each answer

A test that still passes without the code it protects proves nothing.

**Manual end-to-end runs:**
- **Offline:** I ran `uv run python -m flightboard --offline` and the full-auto demo (option 6) worked end to end with no network.
- **Missing key:** starting online without an API key printed one clear line and exited with code 2.
- **Live:** I ran the application against the live Swedavia API, going through the menu and the full-auto demo, and it worked.

### Improvements and optimisation
**Using less of the API quota:**
- **A response cache:** recent answers are reused for 120 seconds, so viewing the same list again costs nothing. The cache is a wrapper around any flight source, not part of the client, so it can be switched off or reused without touching the client.
- **Search uses one query, not two:** `flightId eq 'SK1415' and scheduled eq '261124'` finds the flight in both directions at every airport.
- **The destination overview is free:** it's counted from the flights already listed.
- **A cheap heartbeat:** five pings, 2 s apart, with the cost written next to the setting in the code.

**Clearer errors:**
- **One error type per failure:** each kind of failure has its own error type with a message a user can act on:

  | Failure | What the message says |
  |---|---|
  | Bad key | check `SWEDAVIA_API_KEY` |
  | Too many requests | whether it's the 2-second rate limit or the monthly quota |
  | Swedavia unreachable | the server is down or not answering |
  | Rejected filter | Swedavia's reason, plus a hint |
- **One place catches them all:** the menu shows any of them as one line and keeps running.
- **A shorter offline message:** offline mode's "not supported" message went from about 400 characters to one sentence.
- **Clean exits:** a missing key gives a clear message and exit code 2; Ctrl-C or end of input at any prompt says "Goodbye." instead of showing a traceback.

**Rendering:**
- **The original's card:** the flight card copies the original's layout and spacing from the video, with two improvements:
  - both airports are shown as `Name (IATA)`, so the name the original left blank is filled in;
  - times are shown in both UTC and Swedish local time, with the correct zone name in winter and summer (CET/CEST).
- **Paging:** it only asks for input when there's more to show.
- **Honest heartbeat output:** a failed ping never shows a misleading "0 ms", and offline mode pings once, since there's no real network time to measure.

**Offline mode:** `--offline` runs the whole application on one recorded day at Arlanda, with no key and no network. That's useful for demos, for the video, and when the monthly quota is used up. The header says clearly that it's sample data.

### Publishing
The project is public on GitHub: https://github.com/alexander-friberg/flightinfo-api. What's in place:
- **README:** explains what the app is and how to install, configure and run it (online and offline). It also covers how to run the tests, including the live contract test.
- **CI badge:** shows the state of the latest run.
- **Secrets:** the repository contains `.env.example` but never a real `.env`. The gitleaks scan in CI checks the whole history on every push. The only finding ever reported was a made-up test key, which is ignored by its exact fingerprint, so any real secret would still be caught.
- **Documentation:** `research.md`, `api-reference.md`, this document and the work log `PROGRESS.md` are in `docs/`, so the reasoning behind every decision is published with the code.

### Problems and solutions
- **Problem:** A circular import. The menu's option 6 calls the demo, but the demo needed the `App` object and the heartbeat text, which were defined in the menu.
  **Solution:** `App` moved to its own module, and the heartbeat text became plain functions next to the flight card. Both the menu and the demo now import them, and neither imports the other's internals.
- **Problem:** An acceptance criterion with no test behind it. "The HTTP client is closed on exit" was true, but deleting the code that closes it would still have passed every test.
  **Solution:** `main()` got an optional `transport` parameter, used only by tests. A test runs the online path against a fake Swedavia that records whether it was closed, both after quitting normally and after Ctrl-C.
- **Problem:** Typing `²` at the OData menu's "Choose 1-5" would have crashed the program. Python's `"²".isdigit()` is True, but `int("²")` raises an error that the menu doesn't catch.
  **Solution:** The answer is now compared with the allowed values `"1"`–`"5"`, and a test types `²`.
- **Problem:** The test console didn't behave like a real terminal. A flight card is one multi-line string, so the fake recorded it as one "line", and tests couldn't find the card's first line.
  **Solution:** The fake now splits output into lines the way `print` shows them. When a fake behaves differently from the real thing, the fake is what needs fixing.
- **Problem:** Offline mode looked clumsy. An unsupported query showed a message of about 400 characters, and the heartbeat printed five pings of "0 ms".
  **Solution:** The offline message is now one sentence, and the help text after it is worded for the live API so the two never contradict each other. Offline mode pings once.

---

## Phase 4: Problems & solutions (summary)
- **Problem:** Swedavias API portal being inconsistent.
  **Solution:** Since access to the portal was spotty, it became more a matter of luck than consistent access to the site. 
- **Problem:** Minor issues and slight miscommunication with the agent.
  **Solution:** The scope is generally too big and implementation is larger than what i originally planned, which is my fault for not properly explaining this.

---

## Conclusion
All of this resulted in a robust app that delivers constructed flight data to the user and gave me an opportunity to get familiar with an agentic workflow.
It also resulted in a more secure application since risks like the API key being in plaintext were dealt with, i.e putting the API key in a .env file.
I learned how CI is implemented (although in a smaller scale) and how TDD (Test Driven Development) works.
Some improvements i see is the sheer amount of code for something that doesnt really need to be this big. I was wanting a bit more SRP / proper file structure and some general tests but the actual implementation resulted in a much higher volume of test code tham actual production code.
