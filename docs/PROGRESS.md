# Progress log

The agent appends one entry per task (newest at the bottom). Alex uses this log as raw material
for Phases 2–4 of `documentation.md` and for the video.

## Template

```
## Task NN – <title> (YYYY-MM-DD)
- **Built:** what now exists
- **Decisions:** choices made and why (including answers from Alex)
- **Problems & solutions:** what went wrong or was unclear, and how it was solved
- **Deviations from plan:** anything done differently from the task file or docs, and why
- **Live API calls used:** number (0 for most tasks)
```

---

## Task 01 – Project skeleton and tooling (2026-11-24)
- **Built:** `pyproject.toml` (src layout, package `flightboard`, Python >=3.12, runtime dependency `httpx`, dev group pytest/pytest-cov/ruff/mypy, built with the `uv_build` backend) and `uv.lock`. Empty layer packages `domain`, `api`, `services`, `cli`, `data`. `python -m flightboard` prints a placeholder line. A stub `README.md`, `.env.example` with an empty `SWEDAVIA_API_KEY=`. `tests/test_smoke.py` (7 tests) imports every layer and runs `python -m flightboard` in a subprocess, the way a user starts it. ruff, mypy `--strict` and pytest all pass, so the Stop hook now enforces them on every turn.
- **Decisions:**
  - `uv_build` as the build backend: it ships with uv, so no extra build tool to learn or pin.
  - The smoke test runs the app as a subprocess instead of calling `main()` directly, because that also proves the package is installed and `-m` works.
  - mypy checks against Python 3.12 (`python_version = "3.12"`), the minimum the project supports. Development runs on 3.14, so without this, code using 3.13+ standard-library features would pass locally and break for 3.12 users (reviewer's suggestion).
- **Problems & solutions:**
  - `uv sync` failed at first because `pyproject.toml` points at `README.md`, which didn't exist yet. Solved by writing the stub README before syncing.
  - Once `pyproject.toml` existed, the format-after-edit hook (`ruff format .`) started running for real. This ruff version also formats Python code blocks *inside Markdown*, and it silently "tidied" the verbatim quote of the original app's `_is_valid_flight()` in `research.md`, which changed the historical record. Solved by excluding `*.md` from ruff in `pyproject.toml` and restoring `research.md` from git. Lesson: an automatic formatter can change files you never meant it to touch, so check `git status` for files outside the task after hooks run.
- **Deviations from plan:** two config lines beyond the criteria (the Markdown exclusion and mypy's `python_version`), both explained above. The `.gitignore` criterion was already met by the setup commit, so the file didn't change.
- **Live API calls used:** 0

## Task 02 – CI workflow (2026-11-24)
- **Built:** `.github/workflows/ci.yml` with two jobs on every push and pull request.
  - `checks`: Python 3.12 and 3.13 matrix, `uv sync --locked`, then ruff, ruff format, mypy and pytest with coverage. These are the same checks the local Stop hook runs.
  - `secrets`: gitleaks over the whole git history.
  
  The workflow has read-only permissions and uses no secrets at all. Also a CI badge in `README.md`, and `tests/test_ci_workflow.py` (6 tests) that pin the workflow's guarantees, so a later edit can't quietly drop one.
- **Decisions:**
  - Action versions were checked against each action's README on the day: `actions/checkout@v7`, `astral-sh/setup-uv@v10`.
  - Secret scanning uses the **gitleaks CLI** (v8.30.1, latest release), downloaded and checked against the SHA-256 from the release's checksums file before unpacking.
  - The workflow tests read the YAML as text instead of parsing it, because PyYAML would be a new dependency (it needs Alex's approval) for six checks. Each test is scoped to its job, so a step moved to the wrong job is caught.
  - `persist-credentials: false` on the scan job's checkout keeps the GitHub token out of `.git/config` while gitleaks runs.
- **Problems & solutions:**
  - The task assumed `gitleaks/gitleaks-action` plus `fetch-depth: 0` scans the full history. The reviewer doubted it, and reading the action's source confirmed it doesn't: on `push` it scans only the pushed commits (`first^..last`), and on `pull_request` only the PR's commits. Full history is scanned only on manual or scheduled runs. Anything committed before CI existed (for example the first commit) would never have been scanned. Solved by running the gitleaks CLI directly with `--log-opts="--all"`. Lesson: "fetch the whole history" and "scan the whole history" are different things. Check what a tool actually does, not what its example suggests.
  - The gitleaks-action v2 that most tutorials show stopped working after 2026-09-16 (Node 20 runtime end-of-life), so copying an older example would have produced a broken pipeline.
  - The first version of the tests had gaps the reviewer pointed out: both matrix legs could silently run the same Python, and the "live tests excluded" check only looked for the word "live". Both tests now check the actual wiring.
  - The gitleaks README says the project is now "feature complete" and receives security patches only (its author moved to a successor project). That's fine for a pinned scanner, but worth revisiting later.
- **Deviations from plan:**
  - The gitleaks CLI instead of gitleaks-action (reason above).
  - The badge uses the real repo path `alexander-friberg/flightinfo-api` instead of a placeholder, because the remote already existed.
  - Gitleaks hasn't been run locally (the agent's shell blocks `curl`), so its first real run is in CI. If it reports a false positive, add an allowlist entry in `.gitleaks.toml` with a reason; don't narrow the scan.
- **Live API calls used:** 0
- **Pending (Alex):** push and confirm the workflow is green on GitHub, then record the result in the next task's entry.

## Task 03 – Configuration and secrets (2026-11-24)
- **Built:** `src/flightboard/config.py`.
  - A frozen `Settings` (`api_key`, `base_url`, `timeout_s`, `cache_ttl_s`), plus `ConfigError`.
  - `load_settings(env, *, offline=False)`, which reads only the mapping it is given.
  - A missing or blank `SWEDAVIA_API_KEY` stops the app with a message that says exactly what to do: copy `.env.example` to `.env`, then run with `uv run --env-file .env`, or use `--offline`.
  - `repr()`/`str()` show `api_key='***'`.
  - `SWEDAVIA_TIMEOUT_S` / `SWEDAVIA_CACHE_TTL_S` overrides are validated, and an error names the variable and the bad value.
  - `tests/test_config.py` (21 tests) uses plain dicts as the environment.
- **Decisions:**
  - **The environment is a parameter, not `os.environ`.** This is dependency injection at its smallest: tests pass a dict, and only the composition root (task 14) will pass the real `os.environ`. A test proves that a key in the real environment is ignored.
  - **The key is masked in `repr`, not just hidden.** `api_key='***'` shows that a key *is* set, which helps debugging, without showing it.
  - **Offline mode drops the key**, even if one is set. The reviewer spotted that "empty key = offline" was only true one way. Blanking it makes offline mode unable to reach the API at all.
  - **Defaults:** timeout 10 s, cache TTL 120 s. A TTL of 0 or less is allowed, because task 08 uses it to switch caching off. A timeout must be > 0, and `nan`/`inf` are rejected (Python's `float()` accepts them).
- **Problems & solutions:**
  - **CI failed on its first run** (Task 02's pending check). GitHub reported "Unable to resolve action `astral-sh/setup-uv@v10`". That action publishes no floating major tag. Its README pins a full commit SHA with a `# v10.4.0` comment, which was misread as "use @v10". Confirmed via the GitHub API that `v10` doesn't exist and `v10.4.0` is commit `1db35dd…`, then pinned that SHA. The `secrets` job passed on that run, so the full-history gitleaks scan of the repo is clean. Lesson: a workflow can only be truly tested by running it on GitHub; local text tests can check its shape, not whether a tag exists. This is committed separately as a CI fix, before this task.
  - `dataclasses.asdict()` and `vars()` bypass the masked `repr`, so the class docstring warns never to log them.
- **Deviations from plan:** none for the task itself. The CI fix (`.github/workflows/ci.yml`, `tests/test_ci_workflow.py`) was made in the same session but belongs in its own commit.
- **Live API calls used:** 0
- **Pending (Alex):** after pushing the CI fix, confirm both `checks` jobs go green.

## Task 04 – Domain model and airports (2026-11-24)
- **Built:**
  - `domain/models.py`:
    - `Direction` (values `A`/`D`, the API's `flightType` codes, so they can go straight into OData filters).
    - `Scope`: DOMESTIC/INTERNATIONAL/SCHENGEN/UNKNOWN, with `from_indicator()` for the API's `diIndicator`.
    - Frozen `FlightTimes`, `Flight` and `HealthStatus`. Every `Flight` field except `direction` defaults to "missing", because the API marks every field optional.
  - `domain/airports.py`:
    - `AIRPORTS`, read-only, in the original's order and naming.
    - `resolve_airport()`, which accepts codes, city names and airport names with or without å/ä/ö.
    - `to_local()`, converting UTC to Europe/Stockholm.
  - 92 new tests (125 total), mostly parametrized.
- **Decisions:**
  - **The domain is pure:** no I/O, no clock, no printing, so it's tested with plain values and needs no fakes at all.
  - **Naive datetimes are rejected** by `FlightTimes` and `to_local`. Python would silently treat a naive time as the machine's local time, which gives wrong-by-one-hour bugs that only appear on some computers. Aware times are normalised to UTC.
  - **Accent folding instead of listing every spelling:** names go through Unicode normalisation (NFKD) with the accent marks removed, so `Göteborg`, `göteborg` and `goteborg` are all the same key. Aliases are written in their natural Swedish spelling and folded the same way.
  - **`Flight.airport_iata`** (not in the task) records which Swedavia airport the flight belongs to. The flight card needs it to show the queried airport's name (the original left it blank), and the airport-less search needs it to say where a result is.
  - "stockholm" is deliberately not an alias: it could mean Arlanda or Bromma.
  - **`tzdata` as a runtime dependency** (Alex approved the `uv add`): Windows has no system timezone database, so without it the app wouldn't even start there, e.g. on a grader's machine.
- **Problems & solutions:**
  - **A DST test failed although the conversion was right.** For the repeated hour when clocks go back in October, Python (PEP 495) deliberately makes `02:30 CET (second time)` compare *unequal* to the same instant in UTC. The test now compares the actual instants (`timestamp()`), and a comment explains why. Lesson: equality between datetimes in different zones isn't always "same moment".
  - Reviewer findings: two tests only checked "something came back" (`is not None`), not the right value, so a wrong airport or a dropped time would still have passed. Both now assert exact values.
  - Reworking the alias table to use natural spellings accidentally dropped the plain `göteborg` alias. The parametrized alias tests caught it immediately.
- **Deviations from plan:** `Flight.airport_iata` and the `tzdata` dependency, both explained above.
- **Live API calls used:** 0
- **CI:** green after the setup-uv fix, run "feat: configuration and secrets". This closes Task 02's pending check.

## Task 05 – Record fixtures and verify the API reference (2026-11-24)
- **Built:**
  - `scripts/record_fixtures.py`, a one-off recorder. The HTTP client, output directory, date, sleep and key are all passed in. `main()` is its tiny composition root.
  - Real responses saved in `tests/fixtures/` for ARN on 2026-11-24: `arrivals_ARN.json` (289 flights), `departures_ARN.json` (277), `query_sample.json` (search without an airport) and `health.json`.
  - A hand-made `ghost_entries.json`: 3 ghosts, 5 valid entries, one per rule in the original's `_is_valid_flight()`.
  - `tests/test_record_fixtures.py` (11 tests, a fake Swedavia built on `httpx.MockTransport`, no network) and `tests/test_contract_live.py`. The live test is excluded by default; run it with `uv run --env-file .env pytest -m live`.
- **Decisions:**
  - **The recorder is tested like app code.** It's "only a script", but it handles the API key and spends quota, so the tests prove that the key only goes in the header, there are ≥ 2 s between calls (the query rate limit), and the script refuses to keep a file that contains the key.
  - **The 6-call budget was planned up front:** 4 fixtures, 1 probe that answers a docs question (is `YYYY-MM-DD` accepted?), and 1 contract-test run. Everything else was answered by analysing the saved files locally.
  - The search fixture uses a **real** flight id taken from the departures response, so it can't miss.
- **Problems & solutions:**
  - **The docs were wrong about the heartbeat:** it returns the JSON string `"IsAlive"`, not `{}`. Task 07 now judges health by the status code and ignores the body. Without the recording, the client would have been built and tested against the wrong body.
  - **I misread a status code.** I first wrote that `DEL` means "delayed"; the reviewer checked the data, and every `DEL` reads **"Deleted"**, about one flight in five. research.md now has the full code table from the data, and an open question about whether deleted flights should be listed. Lesson: read the data, not the abbreviation.
  - **A secret-scanner false positive was avoided before it happened.** The query response has a long base64 `continuationtoken`, which gitleaks' generic rule would likely flag and turn CI red. The app never uses it, so the recorder replaces it with a placeholder, and the existing fixture was fixed in place rather than re-recorded, which would have cost quota.
  - **City names don't match the statistics file one-to-one.** The API appends airport codes (`London LHR`), and some spellings differ (`Addis Abeba` vs `Addis Ababa`). Stripping the code gives 80 of 92 matches. The other 12 (the literal `"Unknown"` plus 11 spellings) are listed in research.md for task 12's alias table.
  - The reviewer also caught a wrong count in my first write-up (it said "84 of 96" instead of "80 of 92"). Corrected.
- **What the live API told us** (details in research.md):
  - `{date}` is a local Swedish day.
  - A query without `airport` works.
  - `scheduled` accepts `YYMMDD` and `YYYY-MM-DD`.
  - `airlineOperator.icao` really is the ICAO code.
  - Missing fields are omitted rather than empty.
  - There were no ghost entries in today's data.
  - Query items have no `scheduledDate`.
- **Deviations from plan:**
  - The heartbeat finding changed task 07's health criterion and added a ⚠ note in `api-reference.md`, both outside this task's own files.
  - `pyproject.toml` now type-checks `scripts/` and puts the repo root on pytest's path, so the tests can import the script.
  - The `type`/`airline` filter question and whether heartBeat counts against the quota stay unverified: no budget left, and the quota isn't visible in responses.
- **Live API calls used:** 6 (5 recording, 1 contract test).

## Task 06 – Parser and ghost-entry validation (2026-11-24)
- **Built:** `api/parsing.py`, the edge where raw JSON becomes `Flight` objects:
  - `is_valid_flight()`, the original's ghost rule, unchanged
  - `parse_flights(payload, direction)` for arrivals and departures
  - `parse_query(payload)` for query results, where each item wraps an `arrival` or a `departure`
  
  `tests/test_parsing.py` has 40 tests (176 in total): the real ARN fixtures (289 arrivals, 277 departures), one real flight (FR4679) checked field by field, the ghost fixture, and hand-made broken inputs.
- **Decisions:**
  - **Every lookup is defensive.** A missing key, an empty or whitespace-only string, or a value of the wrong type all become `None`. Task 05 showed the API leaves missing fields out entirely, so nothing can assume a key exists. Bad input never raises.
  - **Unparsable timestamps become "missing"**, not errors, so one broken time can't stop a whole list from loading. Times without an offset are read as UTC, because every field is named `…Utc`. Times with an offset are converted to UTC.
  - **One table instead of if/else:** arrivals and departures mirror each other (`arrivalTime` vs `departureTime`, origin vs destination), so a small `_Keys` table per direction drives one shared function.
  - **The original's ghost rule is kept exactly, quirk included.** `arrivalTime or departureTime` picks a non-empty `arrivalTime` even when only `departureTime` has the scheduled time. The task asks for the original's semantics, real data never mixes the two keys, and a test pins the quirk so nobody "fixes" it by accident.
  - The flight's own airport comes from `flightLegIdentifier`, falling back to the response header. Query results have no header.
  - `Flight` from task 04 needed no changes; its field names matched the real data.
- **Problems & solutions:**
  - **CI's secret scan failed on the previous push (task 05).** gitleaks flagged the *made-up* test key in `tests/test_record_fixtures.py` as a possible real API key. Rewriting the line wouldn't help, because the scan covers the whole history and the old commit keeps the line. Solved with gitleaks' own mechanism: a `.gitleaksignore` listing that one finding's fingerprint (commit + file + rule + line), so every other secret is still caught. An inline `# gitleaks:allow` on the line keeps future edits quiet. Committed separately as a CI fix. Lesson: a fake secret that looks realistic will be treated as real, which is good behaviour from the scanner; give test keys low entropy, or mark them.
  - The reviewer pointed out that one test computed its expected value with the function under test (`len(raw) - ghosts` using `is_valid_flight`), so a bug would have cancelled itself out. It now asserts the known counts, 289 and 277.
- **Deviations from plan:** none.
- **Live API calls used:** 0

## Task 07 – FlightSource protocol and HTTP client (2026-11-24)
- **Built:**
  - `api/protocols.py`: the `FlightSource` Protocol (`arrivals`, `departures`, `query`, `health`).
  - `api/errors.py`: `ApiError` plus `AuthError`, `QuotaExceededError`, `ApiUnavailableError` and `BadQueryError`, each with a user-facing message.
  - `api/client.py`: `SwedaviaClient(settings, http, clock)`, the only code that talks to Swedavia.
  - `tests/fakes.py`: `FakeFlightSource` (canned flights, a call log, optional error) for tasks 08–14.
  - 46 new tests (222 total), all through `httpx.MockTransport` with no network.
- **Decisions:**
  - **Three things are injected into the client:**
    - **The `httpx.Client`:** tests pass one whose transport is a plain function playing Swedavia. The real one is built (and closed) by the composition root in task 14.
    - **The settings:** key, base URL and timeout.
    - **A clock:** heartbeat latency is tested with exact numbers and no waiting.
  - **`health()` reports instead of raising.** A heartbeat must produce a result for every ping, so a timeout becomes `ok=False, status_code=None`, and a 503 becomes `ok=False, status_code=503`. Health is judged by status alone, because the body is `"IsAlive"` and not the documented `{}`. The data methods raise typed errors, which the menu will catch (task 13).
  - **Each HTTP status maps to one error type:**
    - 401/403 → `AuthError`, which says to check `SWEDAVIA_API_KEY`.
    - 429 → `QuotaExceededError`, which names the rate limit or the monthly quota when Swedavia's message says which, and both otherwise.
    - 5xx, timeouts and connection failures → `ApiUnavailableError`.
    - 400 on a query → `BadQueryError`, with Swedavia's reason.
    - Anything else → `ApiError` with the status code.
    - 204 → an empty list, not an error.
  - **Keeping the key secret has several layers:**
    1. The key is sent only in a header, never in the URL.
    2. Errors are raised `from None`, so no httpx exception (with its request details) is attached.
    3. Any text from Swedavia's error body is scrubbed of the key before it reaches a message.
    4. Redirects are never followed.
    
    Tests cover each layer, including a fake server that echoes the key back in a 429 and a 400.
  - The test key is `"fake-key"`: low entropy, so gitleaks won't flag it like the earlier realistic-looking one.
- **Problems & solutions:**
  - **A redirect could have leaked the key.** The reviewer pointed out that when httpx follows a redirect to *another* host, it drops the standard `Authorization` header but keeps custom ones, and the subscription key is a custom header (`Ocp-Apim-Subscription-Key`). If the composition root ever enabled `follow_redirects`, the key would go to whatever host the redirect named. Fixed by setting `follow_redirects=False` on every request. The test builds a client *with* redirects enabled and checks that only one request, to Swedavia, is made. I temporarily removed the fix to confirm the test then fails.
  - The first version only checked key-scrubbing on the 429 path. The reviewer noticed that the 400-on-query path also quotes Swedavia's text, so a key-echoing 400 is now tested as well.
- **Deviations from plan:** the live contract test now uses the app's `DEFAULT_BASE_URL` (deferred from task 05). The one-off recorder script keeps its own copy.
- **Live API calls used:** 0

## Task 08 – Short-lived response cache (2026-11-24)
- **Built:** `api/caching.py`, `CachingFlightSource(inner, ttl_s, clock)`. It wraps any `FlightSource` and is itself a `FlightSource`, so nothing that uses it can tell the difference.
  - Arrivals/departures are remembered per (airport, day), and queries per filter string, for `ttl_s` seconds (120 by default, from task 03's settings).
  - `health()` always reaches the inner source, errors are never stored, and a TTL of 0 or less switches caching off.
  - `tests/test_caching.py` has 16 tests using `FakeFlightSource` and a fake clock that the test moves forward by hand (238 total).
- **Decisions:**
  - **Composition instead of inheritance (a decorator):** the cache doesn't extend `SwedaviaClient`. It *wraps* a `FlightSource`, so the same cache works in front of the real client, the offline source (task 09) or a test fake. This is the dependency-injection design paying off: the composition root (task 14) decides whether to put it in front.
  - **An injected clock:** expiry is tested exactly (just before the TTL is a hit, exactly at the TTL is a miss) without waiting two minutes. The default is `time.monotonic` rather than the wall clock, because wall time can jump (NTP sync, daylight saving) and a cache shouldn't.
  - **Defensive copies both ways:** callers get a copy, and the cache stores a copy, so neither a caller nor the inner source can change a cached answer afterwards.
  - Empty results are cached too, so a quiet airport isn't fetched again and again.
  - No eviction. One interactive session only ever asks for a few combinations; this is marked as a `# shortcut:` in the code, with when to change it.
- **Problems & solutions:**
  - **A test that couldn't fail:** run against a cache that never caches, 8 of the 14 first tests still passed. That's expected: "health is never cached", "errors aren't cached" and "TTL 0 means no cache" are things a cache must *not* do, so a cache that does nothing meets them trivially. They exist to stop the real cache from caching too much. The 6 positive tests did fail, which proves they test caching.
  - The reviewer spotted that the store-side copy wasn't tested: the fake always returns fresh lists, so removing that copy broke nothing. A new test uses an inner source that changes its list after returning it. I removed the copy temporarily and confirmed that the test then fails.
- **Deviations from plan:** none.
- **Live API calls used:** 0

## Task 09 – Offline flight source (2026-11-24)
- **Built:**
  - `api/offline.py`: `OfflineFlightSource`, a `FlightSource` that answers from the recorded ARN day (2026-11-24), with a fixed healthy heartbeat and a small query matcher. It needs no network and no key.
  - The sample files ship inside the package (`src/flightboard/data/samples/`), loaded through an injectable loader that defaults to `importlib.resources`.
  - `tests/test_offline.py`: 37 tests (276 total).
- **Decisions:**
  - **The same seam the tests use:** offline mode is just another `FlightSource`, so the rest of the app needs no "if offline" branches. Task 14 picks which source to build.
  - **Honest sample data.** Whatever airport or date you ask for, you get the real recorded ARN day. Flights keep their real airport rather than being relabelled (a "Göteborg" card showing an Arlanda flight would be false). A `label` ("Offline sample data: Stockholm Arlanda, 24 Nov 2026 (recorded), shown for any airport and date") is there for the menu header.
  - **The sample is shipped inside the package, not read from `tests/`**, so it works after installing. Verified by building the wheel, installing it in a throwaway environment and running it from outside the repo.
  - **A deliberately small query matcher:** only `and`-joined `eq` clauses on `flightId`, `airport`, `flightType` and `scheduled`. That's exactly what search and the OData presets produce. Anything else gives a clear "not supported offline" `BadQueryError` instead of a wrong answer. Writing a full OData parser for demo data wasn't worth it.
  - The loader is an injected function, so the tests use a tiny three-flight sample that's easy to reason about, and one test uses the real files.
- **Problems & solutions:**
  - **Offline search would have stopped working the day after recording.** The first version filtered queries by `scheduled`, but the lists ignore the date. Search always sends the chosen date (usually today), so from 25 Nov onward offline search would have found nothing, while "show arrivals" still worked. The reviewer caught it. Fixed by applying one rule everywhere: airport and date are *validated* but don't narrow the sample. Lesson: a fake data source has to be consistent with itself, not just with the real API.
  - **A date parser that was too forgiving.** `strptime("%y%m%d")` happily reads `'2611'` as 1 Jan 2026, so a mistyped date would have quietly matched nothing. The value must now match the exact shape (`\d{6}` or `\d{4}-\d{2}-\d{2}`) before it's parsed.
  - The parser's case handling was inconsistent (`and` matched any case, `eq` didn't). Keywords and the A/D value are now case-insensitive throughout.
- **Deviations from plan:** none to the code. A note was added to task 10's file: the "by status" preset isn't supported offline.
- **Live API calls used:** 0

## Task 10 – Flight services: list, search, OData (2026-11-24)
- **Built:** `services/flights.py`:
  - `FlightService(source)`, with:
    - `arrivals` and `departures`, sorted by scheduled time (no time last, ties by flight id)
    - `search(flight_id, day, airport=None)`, one query
    - `run_query(filter)` for user-written OData
  - `odata_presets(airport, day)`: departures, arrivals, one flight, and cancelled flights.
  
  `tests/test_flight_services.py` has 53 tests (329 total), using `FakeFlightSource` plus a few against the real `OfflineFlightSource`.
- **Decisions:**
  - **"Deleted" flights are listed as-is (Alex's decision).** About one in five flights in the data has status `DEL`; they're real records, and the original had no known filter.
  - **Search is one query across all airports:** `flightId eq 'SK1415' and scheduled eq '261124'`. Typing `sk 1415` works too. That's one API call instead of two (arrivals and departures), and task 05 showed the API needs no airport.
  - **Validate, don't escape.** A flight id or airport typed by the user ends up inside a filter string, so a quote could change the query's meaning ("OData injection", like SQL injection). Ids must be letters and digits after normalising, and airports must be three letters. Anything else is refused *before* any API call. The free-text OData option passes filters through unchanged on purpose, because that option *is* the raw query endpoint.
  - **The "by status" preset is fixed to cancelled flights** (`flightStatus eq 'CAN'`), so it needs no extra prompt. Only the single-flight preset needs a flight id, and a `needs_flight_id` flag lets the menu ask only then.
  - **Helpful errors:** if Swedavia rejects a typed filter, the message gets a hint listing the supported fields and an example.
- **Problems & solutions:**
  - **Two error messages contradicted each other.** Offline, the "Cancelled" preset correctly says "Offline mode only understands flightId, airport, flightType…", but the hint appended after it said `flightStatus` *is* supported. The reviewer caught it. The hint is now worded for a live connection ("With a live connection, Swedavia accepts…"), so both sentences are true, and a test runs that exact case.
  - **The lists accepted any airport value**, while search validated it, and the HTTP client puts the airport straight into the URL path. All three methods now validate it the same way.
  - New tests run search and the presets against the **real** offline source. That locks in task 09's claim that its matcher understands exactly the strings this service builds; before, two modules agreed only by convention.
- **Deviations from plan:** none. The "by status → CAN" choice is recorded in the task file.
- **Live API calls used:** 0

## Task 11 – Health check heartbeat (2026-11-24)
- **Built:** `services/health.py`: `heartbeat(source, count=5, interval_s=2.0, sleep=time.sleep, on_result=None)` returns a `HeartbeatReport`. The report holds every ping's result, successes and failures, and min/avg/max latency over the successful pings (`None` when all fail). `FakeFlightSource` can now play back a scripted series of health results and errors. 14 new tests (342 total).
- **Decisions:**
  - **Like `ping`:** N calls to `/heartBeat` at an interval, then a summary. This is the research decision: it looks like a heartbeat but stays cheap.
  - **`sleep` is injected.** The real app passes `time.sleep`; tests pass `sleeps.append`, which records how long it *would* have waited. The whole series runs instantly, and a test can check the exact wait pattern: between pings, never after the last one.
  - **The summary can't contradict the data.** The counts and latency statistics are computed from the list of results rather than stored separately, and the report is frozen.
  - **One bad ping doesn't stop the series.** If a ping raises an `ApiError` (e.g. 429), it's recorded as a failed ping and the next one still runs, as the task requires.
  - **Quota cost is visible in the code:** the defaults (5 pings, 2 s) are named constants with a comment saying one run costs 5 calls (about 0.5% of a 1 000-call month).
  - An `on_result(number, status)` callback lets the menu (task 13) print each ping as it arrives, instead of waiting ~8 s for the whole report.
- **Problems & solutions:**
  - The first immutability test only checked that `results` was a tuple, so it would still pass if the report stopped being frozen. The reviewer pointed this out; the test now tries to change the report and expects an error. Lesson: a test for a guarantee must fail when the guarantee is removed.
  - The reviewer noticed that a failed ping has `latency_ms=0.0`, which a careless printer would show as "0.0 ms". That's a display concern, so a note was added to task 13 rather than changing the data.
  - `documentation.md` said the heartbeat tests use a `FakeClock`. They use a recording fake sleep instead (the latency is measured inside the client, task 07). One line corrected.
- **Deviations from plan:** `tests/fakes.py` gained the scripted health mode. Small doc fixes in `documentation.md` and task 13's notes.
- **Live API calls used:** 0

## Task 12 – Destination statistics (2026-11-24)
- **Built:**
  - `scripts/build_city_country.py` reads Swedavia's 2025 statistics (`land-fpl` sheet) and writes `src/flightboard/data/city_country.json`: **345 cities in 67 countries**.
  - `data/lookup.py`: `CityCountryLookup` matches the API's city names to that file, and `load_lookup()` reads the shipped JSON through an injectable reader.
  - `services/destinations.py`: `destination_overview(...)` counts flights per city for arrivals, departures or both, with one filter, and lists unmatched cities separately.
  - 48 new tests (415 total).
- **Decisions:**
  - **A build script, not a hand-edited file.** The JSON is generated from the official Excel file, and rerunning the script gives a byte-identical file (sorted keys). That makes the data reproducible: next year's statistics are one command away. The script skips subtotal rows (`… Summa`) and placeholders (`(tom)`, `UNKNOWN`), and refuses a city listed under two countries.
  - **Data and fixes kept apart:** the JSON holds only what's in the Excel file. The handful of spelling differences between the API and the statistics (`Addis Abeba` vs `Addis Ababa`, `Munich` vs `München`, …) are a small alias table in code, where they're visible and reviewable.
  - **Tolerant matching:** case, extra spaces and å/ä/ö are ignored (the same `fold()` as the airport names), and a trailing airport code is stripped, so `London LHR`, `London LGW` and `London STN` count as one "London".
  - **One filter, like the original:** `destinationer.py` had a single `Filter?` prompt, so one text matches either the city or the country.
  - The service reuses `FlightService` to fetch, so airport validation and sorting are identical to the menu's, and only the requested direction is fetched (each fetch costs quota).
  - New dev dependency `openpyxl` (with its type stubs) to read Excel, approved by Alex. It's only used by the build script, never by the app.
- **Problems & solutions:**
  - **"Not found" really was in the data.** In task 05 I listed Munich, Malta and Charleroi as having "no obvious match" in the statistics. The reviewer found `München`, `Valetta` (Malta's capital, in the file's spelling) and `Brussels` (Charleroi is Brussels-South Charleroi airport) right there. My search for "munch" missed `München` because of the ü. With three more aliases, every city in the recorded data now resolves except the API's own "Unknown", and a test locks that in. Lesson: when searching data with accents, fold the search too, as the app does.
  - **One city, two rows:** counting used the raw spelling while the lookup and filter ignored case, so "Oslo" and "OSLO" would have been two rows. Counting now groups by the folded name and shows the first spelling.
  - The original's "263 cities / 59 countries" doesn't apply: this year's file has 345/67. The data test checks the counts the build script reported, plus known cities (Tirana → ALBANIA) and that no two spellings disagree on a country.
- **Deviations from plan:** `fold()` in `domain/airports.py` became public for reuse. research.md's alias table and city count were corrected, and a note was added to task 13 about the function signature.
- **Live API calls used:** 0

## Task 13a – CLI building blocks: console, prompts, flight card, paging (2026-11-24)
- **Built:**
  - `cli/io.py`: `Console(read, write)`.
  - `cli/prompts.py`: `choose_airport` and `choose_date`.
  - `cli/render.py`: `render_flight`, the original's flight card.
  - `cli/pager.py`: `page`, 50 per page with Enter / `a` / `q`.
  - `ScriptedConsole` in `tests/fakes.py`.
  - 42 new tests (459 total).
- **Decisions:**
  - **Input and output are injected.** The CLI never calls `input()` or `print()` itself; it receives a `Console` holding two functions. The app will pass `input`/`print` (task 14). Tests pass `ScriptedConsole`, which answers from a list and records every line, so a whole conversation can be tested as plain strings. "Today" is passed in too, so the date prompt never reads the system clock.
  - **Snapshot tests for the card:** the expected card is written out character for character, so any spacing change fails a test. Two snapshots use real recorded flights: FR4679, an arrival whose local time crosses midnight (23:50 UTC → 00:50 CET), and AY808, a "Deleted" departure with no gate. The fixtures are November data (CET), so the summer (CEST) snapshot uses a hand-built July flight.
  - **Faithful layout, one deliberate change:** labels and their uneven spacing are copied from the video. The original showed the other airport as `London LHR` and left the queried airport's name blank (`(ARN)`). The recreation writes both as `Name (IATA)` and fills the name in from `AIRPORTS`. This is recorded as a decision in research.md.
  - **Strict dates:** `YYYY-MM-DD` must have exactly that shape before it's parsed, because Python's `date.fromisoformat` also accepts `20261124`. The keywords now/today/tomorrow/yesterday and empty input (= today) work in any letter case.
  - **Paging asks only when needed:** no prompt when everything fits on one page; `a` shows the rest without asking again; any other answer asks again.
- **Problems & solutions:**
  - **A detail missing from the research:** the reviewer flagged the `─` line under each card as undocumented. Checking the video screenshot again showed it *is* there; it had been dropped when the card was copied into research.md. research.md is fixed, so the code and the record agree.
  - **Extra spaces in API names:** a new test showed that `"London  LHR "` (double and trailing spaces) would print as `London  LHR (LHR)`. Names are now whitespace-normalised before the code is stripped, and a bare `"LHR"` prints as `(LHR)`.
  - mypy caught a variable reused with two types in `choose_airport` (a `str` in the listing loop, then `str | None` from `resolve_airport`), which was renamed. ruff asked for Python 3.12's own generic syntax, `def page[T](...)`, instead of a `TypeVar`.
- **Deviations from plan:**
  - The airport-line format, and the CEST snapshot using a hand-built flight (both above).
  - The pager gained an `empty_message` parameter, so destinations (13b) can say something other than "No flights found.".
- **Live API calls used:** 0

## Task 13b – CLI menu and option flows (2026-11-24)
- **Built:**
  - `cli/menu.py`:
    - `App`, the bundle of everything the menu needs: console, flight source, city lookup, a "today" function, a sleep function, and the title.
    - `run_menu(app)`: the original's six options in English plus "7. Destination overview".
  - `cli/destinations.py`: `run_destination_overview`, the original `destinationer.py` flow as option 7.
  - `tests/test_menu.py` and `tests/test_cli_destinations.py` (39 tests, 498 total).
- **Decisions:**
  - **A dispatch table, not an if/elif chain:** the options live in one dict, `{"1": (label, handler), …}`. The menu prints the labels from it and calls the chosen handler, so adding or renaming an option is a one-line change in one place.
  - **One place for errors:** every option runs inside the same `try / except ApiError`, which prints `Error: <message>` on one line and goes back to the menu. This covers API failures (Swedavia down, quota) and input the services reject (a malformed flight number), so no option has its own error handling and none can crash the app with a known error.
  - **Everything injected through `App`:** the menu never creates a client, reads the clock or sleeps for real. The tests build an `App` from `ScriptedConsole`, `FakeFlightSource`, a fixed date and a recording sleep, and drive complete sessions as lists of answers ("7", "arn", "", "germany", "3", "q"). Task 14 builds the real `App`.
  - **The heartbeat output follows the task 11 note:** failed pings never show a time, so there's no "0.0 ms" for something that never answered.
  - Option 6 prints a placeholder until the demo exists (task 14), marked as a shortcut in the code.
- **Problems & solutions:**
  - **A missing menu line:** the menu handled `q` but never printed `q. Quit`; the first test of the menu text caught it.
  - **The test console didn't behave like a terminal:** a flight card is one multi-line string, so `ScriptedConsole` recorded it as a single "line" and the tests couldn't find `[1] → SK1 …`. The fake now splits on newlines, as `print` shows it. When a fake differs from the real thing, fix the fake.
  - **A crash on unusual input:** the reviewer found that typing `²` at option 4's "Choose 1-5" would crash the app. `"²".isdigit()` is True, but `int("²")` raises `ValueError`, which isn't an `ApiError`, so the menu wouldn't catch it. The answer is now compared against the allowed strings `"1"`–`"5"`, and a test types `²`. Lesson: `isdigit()` means "is a Unicode digit", not "is 0–9".
  - **Smoke test on real data:** I ran the real menu with the real offline source and scripted answers. Search, the destination table (filter "germany": Frankfurt 18, Berlin 8, Munich 8, …) and the offline "Cancelled flights" message all behaved. It also showed that offline mode's message is about 400 characters and offline heartbeats show "0 ms"; both are noted for task 14, which owns offline wiring.
  - The reviewer pointed out that option 7's errors weren't covered by the error test, and that the table header appeared above "No destinations found."; both fixed.
- **Deviations from plan:** none. Follow-ups for task 14 are in its Notes.
- **Live API calls used:** 0

## Task 14 – Composition root, full-auto demo, --offline (2026-11-24)
- **Built:**
  - `__main__.py`, the composition root. `uv run --env-file .env python -m flightboard` runs against the live API. `uv run python -m flightboard --offline` runs on recorded sample data with no key and no network.
  - `cli/demo.py`: option 6's full-auto demo.
  - `cli/app.py`: `App`, moved out of the menu.
  - `tests/test_demo.py` and `tests/test_main.py` (15 tests, 513 total).
  
  **The app is feature-complete.**
- **Decisions:**
  - **One place builds everything real:** only `__main__.py` creates the `httpx.Client`, `SwedaviaClient`, cache, offline source, clock, sleep and console (`input`/`print`). Everything else receives them. That's what makes all 513 tests possible without a network. Online, the parts are stacked as menu → `CachingFlightSource` → `SwedaviaClient` → `httpx.Client`, and the client sits in a `with` block so it's closed however the program ends.
  - **Friendly exits:**
    - A missing key prints one clear line (copy `.env.example` to `.env`, or use `--offline`) and exits with code 2, with no traceback, before any network object exists.
    - Ctrl-C or end of input at any prompt says "Goodbye." instead of crashing.
  - **Offline is honest:** the header says "Offline sample data: Stockholm Arlanda, 24 Nov 2026 (recorded)…", and the heartbeat pings once, since there's no real latency to measure.
  - **The demo reuses the menu's services**, with no special code path. It runs five headed steps:
    1. arrivals
    2. departures
    3. a search for the first real departure
    4. the departures OData query
    5. three heartbeat pings
    
    It shows 3 cards per list plus "… and N more", and pauses 2.5 s between steps through the injected sleep, a little over the query endpoint's 2-s limit, because steps 3 and 4 are both queries. A failing step prints its error and the demo continues, so one hiccup doesn't spoil a recording.
  - **Two test-only parameters:** `main(argv, transport=None, sleep=time.sleep)`. A test can run the *online* path against a fake Swedavia (`httpx.MockTransport`) with no waiting.
- **Problems & solutions:**
  - **A circular import:** option 6 must call the demo, and the demo needs `App` and the ping text, which lived in `menu.py`. `App` moved to `cli/app.py`, and the ping and summary text became pure functions in `cli/render.py`, next to the flight card.
  - **An acceptance criterion with no test:** the reviewer pointed out that nothing proved the HTTP client is closed: deleting the `with` block would still pass every test. The `transport` parameter fixed that. A fake transport records being closed, and two tests check it, after a normal quit and after Ctrl-C. I removed the `with` temporarily to confirm the test then fails.
  - **The 13b follow-ups:**
    - The offline "not supported" message went from about 400 characters to one sentence.
    - The live-API hint kept its operator list (the reviewer's point: that's what a user needs after a rejected filter).
    - Offline heartbeats went from five "0 ms" lines to one.
  - Task 01's smoke test expected the old placeholder output; it now runs `python -m flightboard --help` and checks for `--offline`.
- **Manual checks:**
  - `printf '6\nq\n' | uv run python -m flightboard --offline` ran the whole demo with no network (search found SK1415, the OData filter was printed).
  - Running online without a key printed the message and exited with 2.
- **Deviations from plan:** the test-only `transport`/`sleep` parameters on `main`, and `App` moving to its own module.
- **Live API calls used:** 0. The online path is covered with a fake transport; a real live run is the natural next manual check.

## Correction: no menu option 7 (2026-11-24)
- **What was wrong:** the recreation had a seventh menu option, "Destination overview". The original's menu (video) has exactly six options.
- **How it happened:** during planning I proposed two things for `destinationer.py`: a menu option 7, *and* an optional separate command (`python -m flightboard.destinations`). Alex answered "Drop the wrapper". I read that as approval of everything else, so option 7 went into research.md, tasks 12 and 13b, and the code. Alex had only rejected the separate command. Lesson: when someone answers one part of a multi-part proposal, confirm the other parts explicitly instead of assuming silence means yes.
- **What changed (Alex's decision): the menu keeps the original six options, and the overview is part of options 1 and 2.**
  - After the arrivals or departures list, the app asks "Show destination overview (cities, countries, flight counts)? [y/N]". Enter means no, so the normal flow costs one keypress at most.
  - `y` asks for the original's optional filter and shows the same city | country | count table, plus the cities missing from the statistics file.
  - The overview is built from the flights **already fetched** for the list, through a new pure function `summarise_destinations(flights, lookup, match)`, so it makes no second API call even without the cache. `destination_overview(...)` now fetches and then calls it.
  - Consequence: the original's "3 both" choice isn't in the UI, because each option has one direction. It remains available as a library function.
- **Considered:** removing the feature entirely. It's about 250 lines of code, about 500 lines of tests, the city data and the `openpyxl` dev dependency. It was kept, because the original's project description highlights it (the offline city database).
- **Code:** `cli/destinations.py` now has `offer_destination_overview(console, flights, lookup)`; `run_destination_overview` and the 1–3 prompt are gone. `cli/menu.py` has no option 7; options 1 and 2 call the offer after the pager.
- **Tests:**
  - `test_menu.py`: the menu text is six options plus `q`; "7" is now an unknown choice; options 1/2 offer the overview with no extra source call; declining; no offer after search or OData.
  - `test_cli_destinations.py` was rewritten for the offer flow.
  - `test_destinations.py` gained tests for `summarise_destinations`.
  - 521 tests in total.
- **Manual check:** `--offline`, option 1 at ARN, `y`, filter "germany" showed the six-option menu, the arrivals list, then Frankfurt 9, Berlin 4, Munich 4, Düsseldorf 2, Hamburg 1 (arrivals only).
- **Docs:** research.md (the endpoints table, the destinationer.py decision with this history, the Decisions row), documentation.md's file tree, and notes in tasks 12 and 13b.
- **Live API calls used:** 0
- **Review notes (accepted as-is):** the overview is still offered after `q` in the pager. `q` only stops paging the list, and Enter declines the offer. `destination_overview` and `Which` are now used only by tests; they stay as a library function for the "both" case.
