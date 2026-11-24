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
