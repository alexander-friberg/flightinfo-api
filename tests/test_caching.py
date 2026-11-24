from collections.abc import Callable
from datetime import date

import pytest

from flightboard.api.caching import CachingFlightSource
from flightboard.api.errors import ApiUnavailableError
from flightboard.api.protocols import FlightSource
from flightboard.domain.models import Direction, Flight, HealthStatus
from tests.fakes import FakeFlightSource

DAY = date(2026, 11, 24)
TOMORROW = date(2026, 11, 25)
TTL = 120.0
ARRIVAL = Flight(direction=Direction.ARRIVAL, flight_id="SK1")
DEPARTURE = Flight(direction=Direction.DEPARTURE, flight_id="SK2")


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def cached(
    inner: FakeFlightSource | None = None, ttl_s: float = TTL
) -> tuple[CachingFlightSource, FakeFlightSource, FakeClock]:
    inner = inner or FakeFlightSource(arrivals=[ARRIVAL], departures=[DEPARTURE], query=[ARRIVAL])
    clock = FakeClock()
    return CachingFlightSource(inner, ttl_s=ttl_s, clock=clock), inner, clock


def test_cache_satisfies_the_flight_source_protocol() -> None:
    """Checked by mypy: the assignment fails type-checking if a method is missing or wrong."""
    cache, _, _ = cached()

    source: FlightSource = cache

    assert source is cache


ListMethod = Callable[[CachingFlightSource, str, date], list[Flight]]
LIST_METHODS = [CachingFlightSource.arrivals, CachingFlightSource.departures]


@pytest.mark.parametrize("method", LIST_METHODS)
def test_repeat_within_ttl_is_served_from_the_cache(method: ListMethod) -> None:
    cache, inner, clock = cached()

    first = method(cache, "ARN", DAY)
    clock.advance(TTL - 0.001)
    second = method(cache, "ARN", DAY)

    assert first != []
    assert second == first
    assert inner.call_count == 1


@pytest.mark.parametrize("method", LIST_METHODS)
def test_entry_expires_when_the_ttl_has_passed(method: ListMethod) -> None:
    cache, inner, clock = cached()

    method(cache, "ARN", DAY)
    clock.advance(TTL)
    method(cache, "ARN", DAY)

    assert inner.call_count == 2


def test_query_entries_expire_too() -> None:
    cache, inner, clock = cached()

    cache.query("flightId eq 'SK1'")
    clock.advance(TTL)
    cache.query("flightId eq 'SK1'")

    assert inner.call_count == 2


def test_an_expired_entry_is_refreshed_and_then_cached_again() -> None:
    cache, inner, clock = cached()

    cache.arrivals("ARN", DAY)
    clock.advance(TTL + 1)
    cache.arrivals("ARN", DAY)
    clock.advance(1)
    cache.arrivals("ARN", DAY)

    assert inner.call_count == 2


def test_different_airports_days_and_directions_are_separate_entries() -> None:
    cache, inner, _ = cached()

    cache.arrivals("ARN", DAY)
    cache.arrivals("GOT", DAY)
    cache.arrivals("ARN", TOMORROW)
    cache.departures("ARN", DAY)
    misses = inner.call_count
    cache.arrivals("ARN", DAY)

    # The fake answers every key with the same data, so only the calls can show separate keys.
    assert misses == 4
    assert inner.call_count == 4


def test_query_is_cached_per_filter_string() -> None:
    cache, inner, _ = cached()

    cache.query("flightId eq 'SK1'")
    cache.query("flightId eq 'SK1'")
    cache.query("flightId eq 'SK2'")

    assert [args for _, args in inner.calls] == [("flightId eq 'SK1'",), ("flightId eq 'SK2'",)]


def test_health_is_never_cached() -> None:
    down = HealthStatus(ok=False, status_code=503, latency_ms=9.0, message="HTTP 503")
    cache, inner, _ = cached(FakeFlightSource(health=down))

    assert cache.health() == down
    assert cache.health() == down
    assert inner.call_count == 2


def test_errors_are_not_cached() -> None:
    inner = FakeFlightSource(arrivals=[ARRIVAL], error=ApiUnavailableError("down"))
    cache, _, _ = cached(inner)

    with pytest.raises(ApiUnavailableError):
        cache.arrivals("ARN", DAY)
    inner.error = None
    result = cache.arrivals("ARN", DAY)

    assert result == [ARRIVAL]
    assert inner.call_count == 2


@pytest.mark.parametrize("ttl_s", [0.0, -5.0])
def test_zero_or_negative_ttl_disables_caching(ttl_s: float) -> None:
    cache, inner, _ = cached(ttl_s=ttl_s)

    cache.arrivals("ARN", DAY)
    cache.arrivals("ARN", DAY)
    cache.query("flightId eq 'SK1'")
    cache.query("flightId eq 'SK1'")

    assert inner.call_count == 4


def test_callers_cannot_change_what_is_cached() -> None:
    cache, _, _ = cached()

    cache.arrivals("ARN", DAY).clear()

    assert cache.arrivals("ARN", DAY) == [ARRIVAL]


def test_an_empty_result_is_cached_too() -> None:
    cache, inner, _ = cached(FakeFlightSource())

    assert cache.departures("VBY", DAY) == []
    assert cache.departures("VBY", DAY) == []
    assert inner.call_count == 1


class SharingSource(FakeFlightSource):
    """An inner source that hands out its own list and later changes it."""

    def __init__(self) -> None:
        super().__init__()
        self.shared = [ARRIVAL]

    def arrivals(self, airport: str, day: date) -> list[Flight]:
        super().arrivals(airport, day)
        return self.shared


def test_inner_source_changing_its_list_later_does_not_change_the_cache() -> None:
    inner = SharingSource()
    cache, _, _ = cached(inner)

    cache.arrivals("ARN", DAY)
    inner.shared.append(DEPARTURE)

    assert cache.arrivals("ARN", DAY) == [ARRIVAL]
