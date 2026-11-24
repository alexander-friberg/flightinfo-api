from datetime import date

import pytest

from flightboard.api.errors import ApiUnavailableError
from flightboard.api.protocols import FlightSource
from flightboard.domain.models import Direction, Flight, HealthStatus
from tests.fakes import FakeFlightSource

DAY = date(2026, 11, 24)
ARRIVAL = Flight(direction=Direction.ARRIVAL, flight_id="SK1")
DEPARTURE = Flight(direction=Direction.DEPARTURE, flight_id="SK2")


def test_fake_satisfies_the_protocol_and_returns_canned_data() -> None:
    fake = FakeFlightSource(arrivals=[ARRIVAL], departures=[DEPARTURE], query=[DEPARTURE])
    source: FlightSource = fake

    assert source.arrivals("ARN", DAY) == [ARRIVAL]
    assert source.departures("GOT", DAY) == [DEPARTURE]
    assert source.query("flightId eq 'SK2'") == [DEPARTURE]
    assert source.health().ok is True


def test_fake_records_every_call_in_order() -> None:
    fake = FakeFlightSource()

    fake.arrivals("ARN", DAY)
    fake.query("flightId eq 'SK1'")
    fake.health()

    assert fake.calls == [
        ("arrivals", ("ARN", DAY)),
        ("query", ("flightId eq 'SK1'",)),
        ("health", ()),
    ]
    assert fake.call_count == 3


def test_fake_can_raise_and_still_counts_the_call() -> None:
    fake = FakeFlightSource(error=ApiUnavailableError("down"))

    with pytest.raises(ApiUnavailableError):
        fake.departures("ARN", DAY)

    assert fake.call_count == 1


def test_fake_health_can_be_scripted() -> None:
    down = HealthStatus(ok=False, status_code=503, latency_ms=12.0, message="HTTP 503")
    fake = FakeFlightSource(health=down)

    assert fake.health() == down


def test_fake_returns_copies_so_callers_cannot_change_its_data() -> None:
    fake = FakeFlightSource(arrivals=[ARRIVAL])

    fake.arrivals("ARN", DAY).clear()

    assert fake.arrivals("ARN", DAY) == [ARRIVAL]


def test_fake_health_can_play_a_script_of_results_and_errors() -> None:
    up = HealthStatus(ok=True, status_code=200, latency_ms=5.0)
    fake = FakeFlightSource(health=[up, ApiUnavailableError("down"), up])

    assert fake.health() == up
    with pytest.raises(ApiUnavailableError):
        fake.health()
    assert fake.health() == up
    with pytest.raises(AssertionError, match="script"):
        fake.health()
