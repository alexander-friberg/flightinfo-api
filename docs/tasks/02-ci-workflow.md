# 02 – CI workflow (GitHub Actions)
Status: done
Owner: agent (Alex verifies on GitHub)
Depends on: 01

## Goal
Every push and pull request runs the same checks as the local Stop hook, plus secret scanning.
This proves the project works on a clean machine, not only locally.

## Context
- `docs/documentation.md` → "CI considerations" (decision: base + secret scanning)

## Acceptance criteria
- [x] `.github/workflows/ci.yml` triggers on `push` and `pull_request`
- [x] Job `checks`: matrix Python 3.12 and 3.13, uses `astral-sh/setup-uv`, runs `uv sync --locked`, then ruff check, ruff format --check, mypy, and pytest with `--cov=flightboard --cov-report=term-missing`
- [x] Job `secrets`: runs gitleaks over the full git history (`fetch-depth: 0`)
- [x] No secrets are used or needed by the workflow; live tests stay excluded
- [x] Actions pinned to a major version at least (e.g. `@v4`)
- [x] CI status badge added to `README.md` (repository path left as a placeholder Alex fills in)
- [ ] **Alex:** after committing and pushing, the workflow is green on GitHub (record the result in PROGRESS.md on the next task)

## Out of scope
Deployment, Docker, Dependabot, scheduled live contract tests (possible later stretch goals).

## Notes
- Check the gitleaks-action docs for whether a license key is required. It has historically
  been free for personal accounts but required for organisation-owned repos. If it's needed,
  use the gitleaks CLI directly instead.
- Outcome: no license is needed for a personal-account repo, but the gitleaks CLI is used
  anyway. On `push` and `pull_request`, gitleaks-action scans only the new commits, not the
  full history (confirmed in its source). See PROGRESS.md.
- The badge uses the real repo path (`alexander-friberg/flightinfo-api`) instead of a
  placeholder, because the remote already exists.
