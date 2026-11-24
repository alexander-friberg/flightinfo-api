from datetime import date

import pytest

from flightboard.api.errors import ApiUnavailableError, BadQueryError
from flightboard.data.lookup import CityCountryLookup
from flightboard.domain.models import Direction, Flight
from flightboard.services.destinations import (
    DestinationOverview,
    DestinationRow,
    Which,
    destination_overview,
)
from tests.fakes import FakeFlightSource

DAY = date(2026, 11, 24)
LOOKUP = CityCountryLookup(
    {"Oslo": "NORWAY", "London": "GREAT BRITAIN", "Visby": "SWEDEN", "Bergen": "NORWAY"}
)


def arriving_from(*cities: str | None) -> list[Flight]:
    return [Flight(direction=Direction.ARRIVAL, other_airport_name=c) for c in cities]


def departing_to(*cities: str | None) -> list[Flight]:
    return [Flight(direction=Direction.DEPARTURE, other_airport_name=c) for c in cities]


SOURCE = FakeFlightSource(
    arrivals=arriving_from("Oslo", "London LHR", "Oslo", "London LGW", "Oslo"),
    departures=departing_to("Visby", "Oslo", "Atlantis", "Visby"),
)


def overview(
    which: Which, match: str | None = None, source: FakeFlightSource = SOURCE
) -> DestinationOverview:
    return destination_overview(source, LOOKUP, "ARN", DAY, which, match=match)


def test_counts_unique_cities_sorted_by_count_then_name() -> None:
    result = overview(Which.ARRIVALS)

    assert result.rows == (
        DestinationRow("Oslo", "NORWAY", 3),
        DestinationRow("London", "GREAT BRITAIN", 2),
    )


def test_departures_only() -> None:
    result = overview(Which.DEPARTURES)

    assert result.rows == (
        DestinationRow("Visby", "SWEDEN", 2),
        DestinationRow("Atlantis", "Unknown", 1),
        DestinationRow("Oslo", "NORWAY", 1),
    )


def test_both_merges_arrival_and_departure_counts() -> None:
    result = overview(Which.BOTH)

    assert result.rows[0] == DestinationRow("Oslo", "NORWAY", 4)
    assert sum(r.count for r in result.rows) == 9


def test_spelling_variants_of_one_city_are_one_row() -> None:
    source = FakeFlightSource(departures=departing_to("Oslo", "OSLO", " oslo ", "Visby"))

    result = overview(Which.DEPARTURES, source=source)

    assert result.rows == (
        DestinationRow("Oslo", "NORWAY", 3),
        DestinationRow("Visby", "SWEDEN", 1),
    )


def test_fetches_only_what_was_asked_for() -> None:
    """Each list costs quota, so only the requested direction(s) may be fetched."""
    departures_only = FakeFlightSource()
    both = FakeFlightSource()

    destination_overview(departures_only, LOOKUP, "arn", DAY, Which.DEPARTURES)
    destination_overview(both, LOOKUP, "arn", DAY, Which.BOTH)

    assert {name for name, _ in departures_only.calls} == {"departures"}
    assert sorted(name for name, _ in both.calls) == ["arrivals", "departures"]
    assert {args for _, args in [*departures_only.calls, *both.calls]} == {("ARN", DAY)}


def test_unmatched_cities_become_unknown_and_are_listed_separately() -> None:
    result = overview(Which.DEPARTURES)

    assert DestinationRow("Atlantis", "Unknown", 1) in result.rows
    assert result.unmatched == ("Atlantis",)


def test_the_apis_literal_unknown_is_not_a_lookup_miss() -> None:
    source = FakeFlightSource(departures=departing_to("Unknown", "Unknown", None))

    result = overview(Which.DEPARTURES, source=source)

    assert result.rows == (DestinationRow("Unknown", "Unknown", 3),)
    assert result.unmatched == ()


@pytest.mark.parametrize(
    ("match", "cities"),
    [
        ("norway", ["Oslo", "Bergen"]),
        ("NOR", ["Oslo", "Bergen"]),
        ("osl", ["Oslo"]),
        ("  visby ", ["Visby"]),
        ("britain", ["London"]),
        ("unknown", ["Atlantis"]),
        ("", ["Oslo", "Visby", "Atlantis", "Bergen", "London"]),
        ("nothing-like-this", []),
    ],
)
def test_filter_matches_country_or_city_substring(match: str, cities: list[str]) -> None:
    source = FakeFlightSource(
        arrivals=arriving_from("Oslo", "Oslo", "Oslo", "Visby", "Visby", "Atlantis"),
        departures=departing_to("Bergen", "London LHR"),
    )

    result = overview(Which.BOTH, match=match, source=source)

    assert sorted(r.city for r in result.rows) == sorted(cities)


def test_filter_ignores_swedish_letters() -> None:
    lookup = CityCountryLookup({"Malmö": "SWEDEN"})
    source = FakeFlightSource(departures=departing_to("Malmö"))

    result = destination_overview(source, lookup, "ARN", DAY, Which.DEPARTURES, match="malmo")

    assert [r.city for r in result.rows] == ["Malmö"]


def test_filtered_out_unmatched_cities_are_not_listed() -> None:
    result = overview(Which.DEPARTURES, match="sweden")

    assert result.unmatched == ()


def test_errors_propagate_and_bad_airports_are_rejected() -> None:
    failing = FakeFlightSource(error=ApiUnavailableError("down"))

    with pytest.raises(ApiUnavailableError):
        destination_overview(failing, LOOKUP, "ARN", DAY, Which.ARRIVALS)
    with pytest.raises(BadQueryError):
        destination_overview(FakeFlightSource(), LOOKUP, "A'N", DAY, Which.ARRIVALS)


def test_which_matches_the_originals_1_to_3_menu() -> None:
    assert [w.value for w in Which] == ["1", "2", "3"]
    assert Which("3") is Which.BOTH
