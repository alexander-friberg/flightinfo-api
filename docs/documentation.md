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

## Phase 2: Implementation *(fill in)*

### How the work started
*(Repository setup, first commit, first green CI run.)*

### Project structure
*(Final structure. Note any differences from the plan and why.)*

### What was built first
*(Expected: domain model and parser against fixtures. Explain why starting at the core and working outwards made testing easier.)*

### How the features were developed
*(One short subsection per feature: arrivals/departures, search, OData, health/heartbeat, destinations, demo.)*

### Problems and solutions
- **Problem:** *(e.g. API response differed from the documentation)*
  **Solution:**
- **Problem:** *(e.g. ghost entries / missing fields)*
  **Solution:**
- **Problem:** *(e.g. time zones)*
  **Solution:**

---

## Phase 3: Completion & improvement *(fill in)*

### Finishing the project
### Testing the whole solution
*(Test count, coverage, manual end-to-end run against the live API.)*
### Improvements and optimisation
*(e.g. caching, clearer error messages, rendering.)*
### Publishing
*(GitHub repository, README, CI badge.)*

### Problems and solutions
- **Problem:** *(e.g. worked locally but failed in CI: missing dependency, Python version, path to `city_country.json`)*
  **Solution:**
- **Problem:** *(small bugs at the end)*
  **Solution:**

---

## Phase 4: Problems & solutions (summary) *(fill in)*
- **Problem:** Inconsistent data from the API (ghost entries, missing fields)
  **Solution:**
- **Problem:** No access to the original source code
  **Solution:**
- **Problem:** Limited API quota
  **Solution:**
- **Problem:** *(…)*
  **Solution:**

---

## Conclusion *(fill in)*
### What I achieved
### What I learned
### What could be improved
