"""A `ping`-style heartbeat against the API's health endpoint."""

import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass

from flightboard.api.errors import ApiError
from flightboard.api.protocols import FlightSource
from flightboard.domain.models import HealthStatus

# Quota-friendly: one run is 5 calls (about 0.5% of a 1 000-call month), spread over 8 s.
DEFAULT_COUNT = 5
DEFAULT_INTERVAL_S = 2.0


@dataclass(frozen=True)
class HeartbeatReport:
    """Every ping's result, plus a summary. Latency statistics only count successful pings."""

    results: tuple[HealthStatus, ...]

    @property
    def successes(self) -> int:
        return sum(r.ok for r in self.results)

    @property
    def failures(self) -> int:
        return len(self.results) - self.successes

    @property
    def min_ms(self) -> float | None:
        latencies = self._latencies()
        return min(latencies) if latencies else None

    @property
    def avg_ms(self) -> float | None:
        latencies = self._latencies()
        return statistics.fmean(latencies) if latencies else None

    @property
    def max_ms(self) -> float | None:
        latencies = self._latencies()
        return max(latencies) if latencies else None

    def _latencies(self) -> list[float]:
        return [r.latency_ms for r in self.results if r.ok]


def heartbeat(
    source: FlightSource,
    count: int = DEFAULT_COUNT,
    interval_s: float = DEFAULT_INTERVAL_S,
    sleep: Callable[[float], None] = time.sleep,
    on_result: Callable[[int, HealthStatus], None] | None = None,
) -> HeartbeatReport:
    """Ping `count` times, `interval_s` apart; `on_result(n, status)` fires after each ping."""
    if count < 1:
        raise ValueError(f"count must be at least 1, got {count}")
    if interval_s < 0:
        raise ValueError(f"interval_s can't be negative, got {interval_s}")

    results = []
    for number in range(1, count + 1):
        if number > 1:
            sleep(interval_s)
        status = _ping(source)
        results.append(status)
        if on_result is not None:
            on_result(number, status)
    return HeartbeatReport(tuple(results))


def _ping(source: FlightSource) -> HealthStatus:
    try:
        return source.health()
    except ApiError as error:
        # No response means no latency to report; failures don't count towards the statistics.
        return HealthStatus(ok=False, status_code=None, latency_ms=0.0, message=str(error))
