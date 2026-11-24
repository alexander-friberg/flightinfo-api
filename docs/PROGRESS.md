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
