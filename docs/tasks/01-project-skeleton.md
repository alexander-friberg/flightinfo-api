# 01 – Project skeleton and tooling
Status: done
Owner: agent
Depends on: –

## Goal
A uv-managed Python package with lint, format, type checking and tests wired up. All later tasks
build on it, and the Stop hook starts enforcing checks from here on.

## Context
- `docs/documentation.md` → "Planned file structure", "Choice of tools and techniques"
- `CLAUDE.md` → Commands, Style

## Acceptance criteria
- [x] `pyproject.toml` with a src layout, package `flightboard`, Python `>=3.12`, runtime dependency `httpx`
- [x] Dev dependency group: `pytest`, `pytest-cov`, `ruff`, `mypy`
- [x] Ruff configured: line length 100; rule sets at least `E`, `F`, `I`, `UP`, `B`, `SIM`
- [x] mypy configured in `pyproject.toml`: `strict = true`, `files = ["src", "tests"]`
- [x] pytest configured: `testpaths = ["tests"]`, marker `live` registered, `addopts = "-m 'not live'"`
- [x] Empty package modules for `domain`, `api`, `services`, `cli`, `data`, each with `__init__.py`
- [x] `uv run python -m flightboard` runs and prints a placeholder line
- [x] One smoke test that imports the package (pytest exits 5 when it collects no tests, which would fail the Stop hook)
- [x] `.gitignore` covers `.venv/`, `__pycache__/`, `.env`, `.env.local`, `.coverage`, `.claude/settings.local.json`, `.claude/BLOCKED`
- [x] `.env.example` containing `SWEDAVIA_API_KEY=` (no value)
- [x] Stub `README.md`: project name, one-line purpose, "work in progress"
- [x] All checks pass

## Out of scope
CI (task 02), any app logic.

## Notes
- `.gitignore` was already in place from the setup commit and meets the criterion (`.env.*` with `!.env.example` covers `.env.local`).
- Added `[tool.ruff] extend-exclude = ["*.md"]` and mypy `python_version = "3.12"`; see PROGRESS.md.
