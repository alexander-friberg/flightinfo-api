"""Offline mode: recorded sample data, no network, no key."""

import json
import socket
from datetime import date
from pathlib import Path

import pytest

from flightboard.api.errors import BadQueryError
from flightboard.api.offline import OfflineFlightSource, read_sample
from flightboard.api.protocols import FlightSource
from flightboard.domain.models import Direction, Flight

FIXTURES = Path(__file__).parent / "fixtures"
ANY_DAY = date(2031, 6, 1)


def tiny_loader(name: str) -> str:
    """Two arrivals and one departure, so query matching is easy to follow."""
    samples = {
        "arrivals_ARN.json": {
            "to": {"arrivalAirportIata": "ARN"},
            "flights": [
                {"flightId": "SK532", "arrivalTime": {"scheduledUtc": "2026-11-24T16:25:00Z"}},
                # 23:30 UTC on the 23rd is already the 24th in Stockholm (CET).
                {"flightId": "FR4679", "arrivalTime": {"scheduledUtc": "2026-11-23T23:30:00Z"}},
            ],
        },
        "departures_ARN.json": {
            "from": {"departureAirportIata": "ARN"},
            "flights": [
                {"flightId": "SK532", "departureTime": {"scheduledUtc": "2026-11-24T18:00:00Z"}},
            ],
        },
    }
    return json.dumps(samples[name])


@pytest.fixture
def offline() -> OfflineFlightSource:
    return OfflineFlightSource(loader=tiny_loader)


def ids(flights: list[Flight]) -> list[tuple[str | None, Direction]]:
    return [(f.flight_id, f.direction) for f in flights]


# --- the shipped sample data ---------------------------------------------------------------


@pytest.mark.parametrize("name", ["arrivals_ARN.json", "departures_ARN.json"])
def test_package_ships_the_recorded_samples(name: str) -> None:
    assert json.loads(read_sample(name)) == json.loads((FIXTURES / name).read_text("utf-8"))


def test_works_without_network_or_key(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("offline mode tried to open a network connection")

    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.delenv("SWEDAVIA_API_KEY", raising=False)

    source = OfflineFlightSource()

    assert len(source.arrivals("ARN", ANY_DAY)) == 289
    assert len(source.departures("ARN", ANY_DAY)) == 277
    assert source.health().ok is True


def test_satisfies_the_flight_source_protocol(offline: OfflineFlightSource) -> None:
    """Checked by mypy: the assignment fails type-checking if a method is missing or wrong."""
    source: FlightSource = offline

    assert source is offline


def test_is_clearly_labelled_as_sample_data() -> None:
    label = OfflineFlightSource().label

    assert "sample" in label.lower()
    assert "Stockholm Arlanda" in label
    assert "2026" in label


# --- lists and health -----------------------------------------------------------------------


@pytest.mark.parametrize("airport", ["ARN", "GOT", "KRN"])
def test_serves_the_same_sample_for_any_airport_and_day(
    offline: OfflineFlightSource, airport: str
) -> None:
    flights = offline.arrivals(airport, ANY_DAY)

    assert ids(flights) == [("SK532", Direction.ARRIVAL), ("FR4679", Direction.ARRIVAL)]
    assert {f.airport_iata for f in flights} == {"ARN"}


def test_callers_cannot_change_the_sample(offline: OfflineFlightSource) -> None:
    offline.departures("ARN", ANY_DAY).clear()

    assert len(offline.departures("ARN", ANY_DAY)) == 1


def test_health_is_fixed_and_healthy(offline: OfflineFlightSource) -> None:
    status = offline.health()

    assert status.ok is True
    assert status.message is not None and "offline" in status.message.lower()


# --- query -----------------------------------------------------------------------------------


def test_search_filter_finds_a_sample_flight(offline: OfflineFlightSource) -> None:
    found = offline.query("flightId eq 'SK532' and scheduled eq '261124'")

    assert ids(found) == [("SK532", Direction.ARRIVAL), ("SK532", Direction.DEPARTURE)]


def test_search_in_the_real_sample_finds_the_recorded_flight() -> None:
    found = OfflineFlightSource().query("flightId eq 'AY808' and scheduled eq '261124'")

    assert [(f.flight_id, f.other_airport_iata) for f in found] == [("AY808", "HEL")]


@pytest.mark.parametrize(
    "odata_filter",
    [
        "flightId eq 'AY808' and scheduled eq '310601'",
        "flightId eq 'AY808' and airport eq 'GOT' and scheduled eq '2031-06-01'",
    ],
)
def test_search_for_any_day_or_airport_finds_the_sample_like_the_lists_do(
    odata_filter: str,
) -> None:
    """Offline lists ignore airport and day, so queries must too: searching today still works."""
    found = OfflineFlightSource().query(odata_filter)

    assert [f.flight_id for f in found] == ["AY808"]


@pytest.mark.parametrize(
    ("odata_filter", "expected"),
    [
        ("flightId eq 'sk532'", [("SK532", Direction.ARRIVAL), ("SK532", Direction.DEPARTURE)]),
        ("flightId eq 'SK532' and flightType eq 'D'", [("SK532", Direction.DEPARTURE)]),
        (
            "airport eq 'ARN' and flightType eq 'A'",
            [("SK532", Direction.ARRIVAL), ("FR4679", Direction.ARRIVAL)],
        ),
        (
            "airport eq 'GOT' and flightType eq 'A'",
            [("SK532", Direction.ARRIVAL), ("FR4679", Direction.ARRIVAL)],
        ),
        ("flightId eq 'FR4679' and scheduled eq '2026-11-24'", [("FR4679", Direction.ARRIVAL)]),
        ("flightId eq 'FR4679' and scheduled eq '261123'", [("FR4679", Direction.ARRIVAL)]),
        ("  flightId  eq  'SK532'  AND  flightType eq 'A' ", [("SK532", Direction.ARRIVAL)]),
        ("flightId EQ 'SK532' and flightType eq 'd'", [("SK532", Direction.DEPARTURE)]),
        ("flightId eq 'NOPE'", []),
    ],
)
def test_supported_filters_match_the_sample(
    offline: OfflineFlightSource, odata_filter: str, expected: list[tuple[str, Direction]]
) -> None:
    assert ids(offline.query(odata_filter)) == expected


@pytest.mark.parametrize(
    "odata_filter",
    [
        "flightStatus eq 'DEL'",
        "airport eq 'ARN' or airport eq 'VBY'",
        "(airport eq 'ARN') and flightType eq 'A'",
        "estimated eq '2026-11-24T08:30:00'",
        "scheduled gt '261124'",
        "flightId eq SK532",
        "flightType eq 'X'",
        "scheduled eq 'tomorrow'",
        "scheduled eq '2611'",
        "scheduled eq '26111'",
        "scheduled eq '2026-1-5'",
        "scheduled eq '261340'",
        "airport eq ''",
        "flightId eq 'SK532' and",
        "",
    ],
)
def test_unsupported_filters_say_so_clearly(
    offline: OfflineFlightSource, odata_filter: str
) -> None:
    with pytest.raises(BadQueryError) as raised:
        offline.query(odata_filter)

    message = str(raised.value)
    assert "offline" in message.lower()
    assert "flightId" in message
