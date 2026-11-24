# 11 – Health check heartbeat
Status: done
Owner: agent
Depends on: 07

## Goal
Recreate the original's "heartbeat" health check as a ping-style series: N checks at an interval,
summarised like `ping`.

## Context
- `docs/research.md` → Q "He mentions a heartbeat…" (decision: repeated ping)

## Acceptance criteria
- [x] `services/health.py`: `heartbeat(source, count, interval_s, sleep: Callable[[float], None]) -> HeartbeatReport`
- [x] Report contains each result, success count, failure count, and min/avg/max latency over the successes (`None` when all fail)
- [x] An `ApiError` during one ping counts as a failure and the series continues
- [x] No sleep after the last ping
- [x] Defaults are quota-friendly (e.g. count 5, interval 2 s) and documented
- [x] Optional `on_result` callback so the CLI can print each ping as it happens
- [x] Tests use a fake source with scripted latencies/failures and a recording fake sleep, so no real waiting

## Out of scope
A background heartbeat thread (not planned).

## Notes
- Defaults: 5 pings, 2 s apart (`DEFAULT_COUNT`, `DEFAULT_INTERVAL_S`). One run costs 5 calls.
- A ping that raises `ApiError` is recorded as `HealthStatus(ok=False, status_code=None, latency_ms=0.0)`; statistics only count successes. Task 13's notes say not to print latency for such pings.
- `on_result(n, status)` is 1-based and fires after each ping, before the next sleep.
