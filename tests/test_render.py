"""The flight card, compared as whole strings ("snapshots") so every space is pinned."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flightboard.api.parsing import parse_flights
from flightboard.cli.render import render_flight
from flightboard.domain.models import Direction, Flight, FlightTimes, Scope

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_flight(name: str, direction: Direction, flight_id: str) -> Flight:
    flights = parse_flights(json.loads((FIXTURES / name).read_text("utf-8")), direction)
    [flight] = [f for f in flights if f.flight_id == flight_id]
    return flight


def test_arrival_card_matches_the_original_layout() -> None:
    flight = fixture_flight("arrivals_ARN.json", Direction.ARRIVAL, "FR4679")

    assert render_flight(50, flight) == (
        "[50] → FR4679  |  Ryanair Ltd  (FR)\n"
        "  From  : Gdansk (GDN)\n"
        "  To    : Stockholm Arlanda (ARN)\n"
        "  Status   : Landed 01:08\n"
        "  Terminal : T5    Gate: F35\n"
        "  Baggage  : 6\n"
        "  Sched : 23:50 UTC → 00:50 CET\n"
        "  Est   : 00:08 UTC → 01:08 CET\n"
        "  Actual: 00:08 UTC → 01:08 CET\n"
        "  D/I     : S\n"
        "  ────────────────────────────────────────"
    )


def test_departure_card_has_no_baggage_line_and_shows_missing_values() -> None:
    flight = fixture_flight("departures_ARN.json", Direction.DEPARTURE, "AY808")

    assert render_flight(1, flight) == (
        "[1] → AY808  |  Finnair  (AY)\n"
        "  From  : Stockholm Arlanda (ARN)\n"
        "  To    : Helsinki (HEL)\n"
        "  Status   : Deleted\n"
        "  Terminal : T2    Gate: N/A\n"
        "  Sched : 09:20 UTC → 10:20 CET\n"
        "  Est   : –\n"
        "  Actual: –\n"
        "  D/I     : S\n"
        "  ────────────────────────────────────────"
    )


def test_summer_card_shows_cest() -> None:
    """The fixtures are November data, so the summer case is a hand-built flight."""
    flight = Flight(
        direction=Direction.DEPARTURE,
        flight_id="SK1415",
        airline_name="SAS Scandinavian Airlines",
        airline_iata="SK",
        airport_iata="GOT",
        other_airport_name="London LHR",
        other_airport_iata="LHR",
        status="Departed",
        terminal="D",
        gate="18",
        times=FlightTimes(
            scheduled=datetime(2026, 7, 1, 14, 5, tzinfo=UTC),
            actual=datetime(2026, 7, 1, 14, 12, tzinfo=UTC),
        ),
        scope=Scope.INTERNATIONAL,
    )

    assert render_flight(3, flight) == (
        "[3] → SK1415  |  SAS Scandinavian Airlines  (SK)\n"
        "  From  : Göteborg Landvetter (GOT)\n"
        "  To    : London (LHR)\n"
        "  Status   : Departed\n"
        "  Terminal : D    Gate: 18\n"
        "  Sched : 14:05 UTC → 16:05 CEST\n"
        "  Est   : –\n"
        "  Actual: 14:12 UTC → 16:12 CEST\n"
        "  D/I     : I\n"
        "  ────────────────────────────────────────"
    )


@pytest.mark.parametrize(
    ("name", "code", "shown"),
    [
        ("London LHR", "LHR", "London (LHR)"),
        ("London  LHR ", "LHR", "London (LHR)"),
        ("LHR", "LHR", "(LHR)"),
        ("Gdansk", "GDN", "Gdansk (GDN)"),
        ("Helsinki", None, "Helsinki"),
    ],
)
def test_a_name_that_already_ends_in_its_code_is_not_doubled(
    name: str, code: str | None, shown: str
) -> None:
    flight = Flight(
        direction=Direction.ARRIVAL,
        airport_iata="ARN",
        other_airport_name=name,
        other_airport_iata=code,
    )

    assert f"  From  : {shown}" in render_flight(1, flight).splitlines()


def test_an_almost_empty_flight_renders_with_placeholders() -> None:
    lines = render_flight(7, Flight(direction=Direction.ARRIVAL)).splitlines()

    assert lines[:6] == [
        "[7] → N/A  |  N/A",
        "  From  : N/A",
        "  To    : N/A",
        "  Status   : N/A",
        "  Terminal : N/A    Gate: N/A",
        "  Baggage  : N/A",
    ]
    assert "  D/I     : N/A" in lines


def test_airport_outside_the_ten_shows_just_its_code_and_unknown_scope_is_na() -> None:
    flight = Flight(
        direction=Direction.DEPARTURE,
        airport_iata="XYZ",
        other_airport_iata="OSL",
        scope=Scope.UNKNOWN,
    )

    lines = render_flight(1, flight).splitlines()

    assert "  From  : (XYZ)" in lines
    assert "  To    : (OSL)" in lines
    assert "  D/I     : N/A" in lines
