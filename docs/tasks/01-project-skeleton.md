# 01 – Project skeleton and tooling
Status: todo
Owner: agent
Depends on: –

## Goal
A uv-managed Python package with lint, format, type checking and tests wired up. All later tasks
build on it, and the Stop hook starts enforcing checks from here on.

## Context
- `docs/documentation.md` → "Planned file structure", "Choice of tools and techniques"
- `CLAUDE.md` → Commands, Style

## Acceptance criteria
- [ ] `pyproject.toml` with a src layout, package `flightboard`, Python `>=3.12`, runtime dependency `httpx`
- [ ] Dev dependency group: `pytest`, `pytest-cov`, `ruff`, `mypy`
- [ ] Ruff configured: line length 100; rule sets at least `E`, `F`, `I`, `UP`, `B`, `SIM`
- [ ] mypy configured in `pyproject.toml`: `strict = true`, `files = ["src", "tests"]`
- [ ] pytest configured: `testpaths = ["tests"]`, marker `live` registered, `addopts = "-m 'not live'"`
- [ ] Empty package modules for `domain`, `api`, `services`, `cli`, `data`, each with `__init__.py`
- [ ] `uv run python -m flightboard` runs and prints a placeholder line
- [ ] One smoke test that imports the package (pytest exits 5 when it collects no tests, which would fail the Stop hook)
- [ ] `.gitignore` covers `.venv/`, `__pycache__/`, `.env`, `.env.local`, `.coverage`, `.claude/settings.local.json`, `.claude/BLOCKED`
- [ ] `.env.example` containing `SWEDAVIA_API_KEY=` (no value)
- [ ] Stub `README.md`: project name, one-line purpose, "work in progress"
- [ ] All checks pass

## Out of scope
CI (task 02), any app logic.

## Notes
