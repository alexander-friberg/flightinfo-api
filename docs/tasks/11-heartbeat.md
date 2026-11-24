# 11 – Health check heartbeat
Status: todo
Owner: agent
Depends on: 07

## Goal
Recreate the original's "heartbeat" health check as a ping-style series: N checks at an interval,
summarised like `ping`.

## Context
- `docs/research.md` → Q "He mentions a heartbeat…" (decision: repeated ping)

## Acceptance criteria
- [ ] `services/health.py`: `heartbeat(source, count, interval_s, sleep: Callable[[float], None]) -> HeartbeatReport`
- [ ] Report contains each result, success count, failure count, and min/avg/max latency over the successes (`None` when all fail)
- [ ] An `ApiError` during one ping counts as a failure and the series continues
- [ ] No sleep after the last ping
- [ ] Defaults are quota-friendly (e.g. count 5, interval 2 s) and documented
- [ ] Optional `on_result` callback so the CLI can print each ping as it happens
- [ ] Tests use a fake source with scripted latencies/failures and a recording fake sleep, so no real waiting

## Out of scope
A background heartbeat thread (not planned).

## Notes
