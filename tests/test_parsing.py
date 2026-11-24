import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flightboard.api.parsing import is_valid_flight, parse_flights, parse_query
from flightboard.domain.models import Direction, Flight, FlightTimes, Scope

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def raw_flights(name: str) -> list[dict[str, object]]:
    payload = load(name)
    assert isinstance(payload, dict)
    flights = payload["flights"]
    assert isinstance(flights, list)
    return flights


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


# --- is_valid_flight: the original's rule ------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "valid"),
    [
        ({"flightId": "SK1415"}, True),
        ({"departureAirportEnglish": "Copenhagen"}, True),
        ({"arrivalAirportEnglish": "Oslo"}, True),
        ({"arrivalTime": {"scheduledUtc": "2026-11-24T16:25:00Z"}}, True),
        ({"departureTime": {"scheduledUtc": "2026-11-24T16:25:00Z"}}, True),
        ({"arrivalTime": {}, "departureTime": {"scheduledUtc": "2026-11-24T17:40:00Z"}}, True),
        ({}, False),
        ({"flightId": "", "departureAirportEnglish": "", "arrivalTime": {}}, False),
        ({"airlineOperator": {"name": "SAS"}, "arrivalTime": {"scheduledUtc": ""}}, False),
        ({"flightId": None, "arrivalTime": None}, False),
        # The original's quirk, kept on purpose: a non-empty arrivalTime wins over departureTime
        # even when only departureTime has the scheduled time.
        (
            {
                "arrivalTime": {"estimatedUtc": "2026-11-24T16:30:00Z"},
                "departureTime": {"scheduledUtc": "2026-11-24T16:25:00Z"},
            },
            False,
        ),
    ],
)
def test_is_valid_flight_keeps_the_original_semantics(raw: dict[str, object], valid: bool) -> None:
    assert is_valid_flight(raw) is valid


def test_ghost_fixture_matches_the_original_rule() -> None:
    raw = raw_flights("ghost_entries.json")

    assert [is_valid_flight(f) for f in raw] == [False] * 3 + [True] * 5


# --- parse_flights on the recorded responses --------------------------------------------


@pytest.mark.parametrize(
    ("name", "direction", "count"),
    [
        ("arrivals_ARN.json", Direction.ARRIVAL, 289),
        ("departures_ARN.json", Direction.DEPARTURE, 277),
    ],
)
def test_real_fixtures_parse_fully(name: str, direction: Direction, count: int) -> None:
    flights = parse_flights(load(name), direction)

    # The recorded day had no ghost entries (research.md), so nothing may be dropped.
    assert len(raw_flights(name)) == count
    assert len(flights) == count
    assert all(isinstance(f, Flight) and f.direction is direction for f in flights)
    assert all(f.airport_iata == "ARN" for f in flights)
    assert all(f.flight_id and f.times.scheduled for f in flights)
    assert {f.scope for f in flights} == {Scope.DOMESTIC, Scope.INTERNATIONAL, Scope.SCHENGEN}


def test_one_known_arrival_field_by_field() -> None:
    flights = parse_flights(load("arrivals_ARN.json"), Direction.ARRIVAL)

    [flight] = [f for f in flights if f.flight_id == "FR4679"]

    assert flight == Flight(
        direction=Direction.ARRIVAL,
        flight_id="FR4679",
        airline_name="Ryanair Ltd",
        airline_iata="FR",
        airport_iata="ARN",
        other_airport_name="Gdansk",
        other_airport_iata="GDN",
        status="Landed 01:08",
        terminal="T5",
        gate="F35",
        baggage_belt="6",
        times=FlightTimes(
            scheduled=utc("2026-11-23T23:50:00"),
            estimated=utc("2026-11-24T00:08:30"),
            actual=utc("2026-11-24T00:08:15"),
        ),
        scope=Scope.SCHENGEN,
    )


def test_departures_use_the_destination_and_have_no_baggage_belt() -> None:
    flights = parse_flights(load("departures_ARN.json"), Direction.DEPARTURE)

    [flight] = [f for f in flights if f.flight_id == "AY808"]

    assert flight.other_airport_name == "Helsinki"
    assert flight.other_airport_iata == "HEL"
    assert flight.airport_iata == "ARN"
    assert flight.baggage_belt is None
    assert flight.times.scheduled == utc("2026-11-24T09:20:00")


def test_ghost_entries_are_removed() -> None:
    flights = parse_flights(load("ghost_entries.json"), Direction.ARRIVAL)

    assert len(flights) == 5
    assert [f.flight_id for f in flights if f.flight_id] == ["SK1415"]


# --- missing and broken data -------------------------------------------------------------


def test_a_flight_with_only_an_id_parses_with_everything_else_missing() -> None:
    [flight] = parse_flights({"flights": [{"flightId": "SK1"}]}, Direction.ARRIVAL)

    assert flight == Flight(direction=Direction.ARRIVAL, flight_id="SK1")


def test_empty_strings_and_wrong_types_become_none() -> None:
    raw = {
        "flightId": "SK1",
        "departureAirportEnglish": "",
        "airlineOperator": "not an object",
        "locationAndStatus": {"terminal": 5, "gate": "  "},
        "baggage": None,
        "diIndicator": 7,
    }

    [flight] = parse_flights({"flights": [raw]}, Direction.ARRIVAL)

    assert flight.other_airport_name is None
    assert flight.airline_name is None
    assert flight.terminal is None
    assert flight.gate is None
    assert flight.baggage_belt is None
    assert flight.scope is Scope.UNKNOWN


@pytest.mark.parametrize("bad", ["not a time", "2026-13-40T99:00:00Z", "", 1732460700, None])
def test_malformed_timestamp_is_treated_as_missing(bad: object) -> None:
    raw = {"flightId": "SK1", "arrivalTime": {"scheduledUtc": bad, "actualUtc": bad}}

    [flight] = parse_flights({"flights": [raw]}, Direction.ARRIVAL)

    assert flight.times == FlightTimes()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-11-24T16:25:00Z", utc("2026-11-24T16:25:00")),
        ("2026-11-24T16:25:00", utc("2026-11-24T16:25:00")),
        ("2026-11-24T17:25:00+01:00", utc("2026-11-24T16:25:00")),
        ("2026-11-24T16:25:30.5Z", utc("2026-11-24T16:25:30.500000")),
    ],
)
def test_timestamps_become_aware_utc(text: str, expected: datetime) -> None:
    [flight] = parse_flights(
        {"flights": [{"flightId": "SK1", "departureTime": {"scheduledUtc": text}}]},
        Direction.DEPARTURE,
    )

    assert flight.times.scheduled == expected
    assert flight.times.scheduled is not None
    assert flight.times.scheduled.tzinfo is not None


def test_the_flights_own_airport_wins_over_the_response_header() -> None:
    payload = {
        "from": {"departureAirportIata": "ARN"},
        "flights": [{"flightId": "SK1", "flightLegIdentifier": {"departureAirportIata": "GOT"}}],
    }

    [flight] = parse_flights(payload, Direction.DEPARTURE)

    assert flight.airport_iata == "GOT"


def test_airport_falls_back_to_the_response_header() -> None:
    payload = {"from": {"departureAirportIata": "GOT"}, "flights": [{"flightId": "SK1"}]}

    [flight] = parse_flights(payload, Direction.DEPARTURE)

    assert flight.airport_iata == "GOT"


@pytest.mark.parametrize("payload", [None, {}, {"flights": None}, {"flights": "x"}, [], "IsAlive"])
def test_empty_or_malformed_responses_give_no_flights(payload: object) -> None:
    assert parse_flights(payload, Direction.ARRIVAL) == []
    assert parse_query(payload) == []


def test_non_object_flight_items_are_skipped() -> None:
    payload = {"flights": [None, "x", 3, {"flightId": "SK1"}]}

    assert [f.flight_id for f in parse_flights(payload, Direction.ARRIVAL)] == ["SK1"]


# --- parse_query --------------------------------------------------------------------------


def test_query_fixture_parses() -> None:
    [flight] = parse_query(load("query_sample.json"))

    assert flight.direction is Direction.DEPARTURE
    assert flight.flight_id == "AY808"
    assert flight.airport_iata == "ARN"
    assert flight.other_airport_iata == "HEL"


def test_query_direction_comes_from_the_wrapper_key() -> None:
    payload = {
        "flights": [
            {"arrival": {"flightId": "SK1", "flightLegIdentifier": {"arrivalAirportIata": "GOT"}}},
            {"departure": {"flightId": "SK2"}},
            {"scheduledDate": "2026-11-24"},
            {"arrival": {}},
        ]
    }

    flights = parse_query(payload)

    assert [(f.flight_id, f.direction) for f in flights] == [
        ("SK1", Direction.ARRIVAL),
        ("SK2", Direction.DEPARTURE),
    ]
    assert flights[0].airport_iata == "GOT"


def test_query_item_with_both_wrappers_keeps_both_flights() -> None:
    payload = {"flights": [{"arrival": {"flightId": "SK1"}, "departure": {"flightId": "SK2"}}]}

    flights = parse_query(payload)

    assert [(f.flight_id, f.direction) for f in flights] == [
        ("SK1", Direction.ARRIVAL),
        ("SK2", Direction.DEPARTURE),
    ]
