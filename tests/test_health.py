import dataclasses

import pytest

from flightboard.api.errors import ApiError, ApiUnavailableError, QuotaExceededError
from flightboard.domain.models import HealthStatus
from flightboard.services.health import (
    DEFAULT_COUNT,
    DEFAULT_INTERVAL_S,
    HeartbeatReport,
    heartbeat,
)
from tests.fakes import FakeFlightSource


def ok(ms: float) -> HealthStatus:
    return HealthStatus(ok=True, status_code=200, latency_ms=ms)


def down(code: int | None = 503) -> HealthStatus:
    return HealthStatus(ok=False, status_code=code, latency_ms=12.0, message=f"HTTP {code}")


def run(
    script: list[HealthStatus | ApiError], count: int, interval_s: float = 2.0
) -> tuple[HeartbeatReport, list[float], FakeFlightSource]:
    source = FakeFlightSource(health=script)
    sleeps: list[float] = []
    report = heartbeat(source, count=count, interval_s=interval_s, sleep=sleeps.append)
    return report, sleeps, source


def test_all_pings_succeed() -> None:
    report, _, source = run([ok(40.0), ok(20.0), ok(60.0)], count=3)

    assert [r.latency_ms for r in report.results] == [40.0, 20.0, 60.0]
    assert report.successes == 3
    assert report.failures == 0
    assert report.min_ms == 20.0
    assert report.avg_ms == pytest.approx(40.0)
    assert report.max_ms == 60.0
    assert source.call_count == 3


def test_latency_statistics_use_successes_only() -> None:
    report, _, _ = run([ok(30.0), down(503), ok(50.0), down(None)], count=4)

    assert report.successes == 2
    assert report.failures == 2
    assert (report.min_ms, report.avg_ms, report.max_ms) == (30.0, 40.0, 50.0)


def test_statistics_are_none_when_every_ping_fails() -> None:
    report, _, _ = run([down(500), down(None)], count=2)

    assert report.successes == 0
    assert report.failures == 2
    assert (report.min_ms, report.avg_ms, report.max_ms) == (None, None, None)


def test_an_api_error_counts_as_a_failure_and_the_series_continues() -> None:
    report, _, source = run([ok(10.0), QuotaExceededError("Too many requests"), ok(30.0)], count=3)

    assert source.call_count == 3
    assert [r.ok for r in report.results] == [True, False, True]
    failed = report.results[1]
    assert failed.status_code is None
    assert failed.message == "Too many requests"
    assert (report.min_ms, report.max_ms) == (10.0, 30.0)


def test_sleeps_between_pings_but_not_after_the_last() -> None:
    _, sleeps, _ = run([ok(1.0)] * 4, count=4, interval_s=2.5)

    assert sleeps == [2.5, 2.5, 2.5]


def test_a_single_ping_never_sleeps() -> None:
    _, sleeps, _ = run([ok(1.0)], count=1)

    assert sleeps == []


def test_on_result_reports_each_ping_as_it_happens() -> None:
    source = FakeFlightSource(health=[ok(10.0), ApiUnavailableError("down"), ok(30.0)])
    events: list[str] = []

    heartbeat(
        source,
        count=3,
        interval_s=2.0,
        sleep=lambda s: events.append(f"sleep {s}"),
        on_result=lambda n, status: events.append(f"ping {n} {'ok' if status.ok else 'fail'}"),
    )

    assert events == ["ping 1 ok", "sleep 2.0", "ping 2 fail", "sleep 2.0", "ping 3 ok"]


def test_defaults_are_used_when_not_given() -> None:
    sleeps: list[float] = []
    source = FakeFlightSource()

    report = heartbeat(source, sleep=sleeps.append)

    assert len(report.results) == DEFAULT_COUNT
    assert sleeps == [DEFAULT_INTERVAL_S] * (DEFAULT_COUNT - 1)


@pytest.mark.parametrize(("count", "interval_s"), [(0, 2.0), (-1, 2.0), (3, -0.5)])
def test_invalid_arguments_are_rejected_before_any_ping(count: int, interval_s: float) -> None:
    source = FakeFlightSource()

    with pytest.raises(ValueError):
        heartbeat(source, count=count, interval_s=interval_s, sleep=lambda _: None)

    assert source.call_count == 0


def test_report_is_immutable() -> None:
    """The statistics are derived from `results`, so the results must not change afterwards."""
    report, _, _ = run([ok(1.0)], count=1)

    assert isinstance(report.results, tuple)
    with pytest.raises(dataclasses.FrozenInstanceError):
        report.results = ()  # type: ignore[misc]
