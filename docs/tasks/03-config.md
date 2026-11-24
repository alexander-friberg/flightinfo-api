# 03 – Configuration and secrets
Status: todo
Owner: agent
Depends on: 01

## Goal
A single typed place for configuration, read from the environment, that never exposes the API
key. The original app hard-coded its key at the top of `airport.py`. Fixing that is one of the
project's stated improvements.

## Context
- `docs/research.md` → "Weaknesses in the original", "Access & authentication"

## Acceptance criteria
- [ ] `src/flightboard/config.py` with a frozen `Settings` dataclass: `api_key`, `base_url` (default `https://api.swedavia.se/flightinfo/v2`), `timeout_s`, `cache_ttl_s`
- [ ] `load_settings(env: Mapping[str, str]) -> Settings`, with the environment injected (no direct `os.environ` access inside the function)
- [ ] Missing or empty `SWEDAVIA_API_KEY` raises a clear `ConfigError` telling the user to copy `.env.example` to `.env` and run via `uv run --env-file .env`
- [ ] `Settings.__repr__` / `__str__` mask the key (e.g. `api_key='***'`), with a test proving the key never appears in `repr()`
- [ ] Optional overrides via `SWEDAVIA_TIMEOUT_S` and `SWEDAVIA_CACHE_TTL_S`; invalid numbers give a clear error
- [ ] Offline mode must not require a key: `load_settings(env, offline=True)` (or equivalent) works without one
- [ ] Tests cover all of the above using plain dicts as the environment

## Out of scope
Reading `.env` files in Python. uv handles that via `--env-file`.

## Notes
