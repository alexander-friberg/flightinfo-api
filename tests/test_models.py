import dataclasses
from datetime import UTC, datetime, timedelta, timezone

import pytest

from flightboard.domain.models import Direction, Flight, FlightTimes, HealthStatus, Scope

SCHEDULED = datetime(2026, 1, 15, 16, 25, tzinfo=UTC)


@pytest.mark.parametrize(
    ("indicator", "scope"),
    [
        ("D", Scope.DOMESTIC),
        ("I", Scope.INTERNATIONAL),
        ("S", Scope.SCHENGEN),
        ("d", Scope.DOMESTIC),
        (" s ", Scope.SCHENGEN),
        ("X", Scope.UNKNOWN),
        ("", Scope.UNKNOWN),
        (None, Scope.UNKNOWN),
    ],
)
def test_scope_from_api_indicator(indicator: str | None, scope: Scope) -> None:
    assert Scope.from_indicator(indicator) is scope


def test_direction_values_match_the_api_flight_type_codes() -> None:
    assert Direction.ARRIVAL.value == "A"
    assert Direction.DEPARTURE.value == "D"


def test_flight_times_default_to_missing() -> None:
    assert FlightTimes() == FlightTimes(scheduled=None, estimated=None, actual=None)


def test_flight_times_accept_aware_times() -> None:
    times = FlightTimes(scheduled=SCHEDULED, actual=SCHEDULED + timedelta(minutes=3))

    assert times.scheduled == SCHEDULED
    assert times.actual == SCHEDULED + timedelta(minutes=3)
    assert times.estimated is None


@pytest.mark.parametrize("field", ["scheduled", "estimated", "actual"])
def test_flight_times_reject_naive_datetimes(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        FlightTimes(**{field: datetime(2026, 1, 15, 16, 25)})


def test_flight_times_are_normalised_to_utc() -> None:
    plus_one = timezone(timedelta(hours=1))

    times = FlightTimes(scheduled=datetime(2026, 1, 15, 17, 25, tzinfo=plus_one))

    assert times.scheduled == SCHEDULED
    assert times.scheduled is not None
    assert times.scheduled.utcoffset() == timedelta(0)


def test_flight_with_only_direction_has_every_display_field_missing() -> None:
    flight = Flight(direction=Direction.ARRIVAL)

    assert flight.flight_id is None
    assert flight.airline_name is None
    assert flight.airline_iata is None
    assert flight.airport_iata is None
    assert flight.other_airport_name is None
    assert flight.other_airport_iata is None
    assert flight.status is None
    assert flight.terminal is None
    assert flight.gate is None
    assert flight.baggage_belt is None
    assert flight.times == FlightTimes()
    assert flight.scope is Scope.UNKNOWN


def test_flight_holds_the_card_from_the_video() -> None:
    flight = Flight(
        direction=Direction.ARRIVAL,
        flight_id="SK532",
        airline_name="SAS Scandinavian Airlines",
        airline_iata="SK",
        airport_iata="ARN",
        other_airport_name="London",
        other_airport_iata="LHR",
        status="Scheduled",
        terminal="T5",
        baggage_belt="3",
        times=FlightTimes(scheduled=SCHEDULED),
        scope=Scope.INTERNATIONAL,
    )

    assert flight.gate is None
    assert flight.times.scheduled == SCHEDULED


def test_models_are_frozen() -> None:
    flight = Flight(direction=Direction.DEPARTURE)

    with pytest.raises(dataclasses.FrozenInstanceError):
        flight.flight_id = "SK1"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        flight.times.actual = SCHEDULED  # type: ignore[misc]


def test_health_status() -> None:
    ok = HealthStatus(ok=True, status_code=200, latency_ms=41.5)
    down = HealthStatus(ok=False, status_code=None, latency_ms=10_000.0, message="timed out")

    assert ok.message is None
    assert down.status_code is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        ok.ok = False  # type: ignore[misc]
