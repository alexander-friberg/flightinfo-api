from collections.abc import Callable
from datetime import UTC, date, datetime

import pytest

from flightboard.api.errors import (
    ApiError,
    ApiUnavailableError,
    BadQueryError,
    QuotaExceededError,
)
from flightboard.api.offline import OfflineFlightSource
from flightboard.domain.models import Direction, Flight, FlightTimes
from flightboard.services.flights import FlightService, ODataPreset, odata_presets
from tests.fakes import FakeFlightSource

DAY = date(2026, 11, 24)


def flight(flight_id: str, hour: int | None, direction: Direction = Direction.ARRIVAL) -> Flight:
    scheduled = None if hour is None else datetime(2026, 11, 24, hour, 0, tzinfo=UTC)
    return Flight(direction=direction, flight_id=flight_id, times=FlightTimes(scheduled=scheduled))


def flight_ids(flights: list[Flight]) -> list[str | None]:
    return [f.flight_id for f in flights]


# --- lists --------------------------------------------------------------------------------


def test_arrivals_are_sorted_by_scheduled_time() -> None:
    source = FakeFlightSource(arrivals=[flight("C", 18), flight("A", 6), flight("B", 12)])

    result = FlightService(source).arrivals("ARN", DAY)

    assert flight_ids(result) == ["A", "B", "C"]
    assert source.calls == [("arrivals", ("ARN", DAY))]


def test_departures_are_sorted_with_unscheduled_last_and_ties_by_id() -> None:
    d = Direction.DEPARTURE
    source = FakeFlightSource(
        departures=[
            flight("Z9", None, d),
            flight("SK2", 9, d),
            flight("AY1", 9, d),
            flight("B", 7, d),
        ]
    )

    result = FlightService(source).departures("GOT", DAY)

    assert flight_ids(result) == ["B", "AY1", "SK2", "Z9"]
    assert source.calls == [("departures", ("GOT", DAY))]


def test_deleted_flights_are_listed_as_is() -> None:
    deleted = Flight(direction=Direction.ARRIVAL, flight_id="SK9", status="Deleted")
    source = FakeFlightSource(arrivals=[deleted])

    assert FlightService(source).arrivals("ARN", DAY) == [deleted]


# --- search -------------------------------------------------------------------------------


def test_search_makes_one_query_without_airport_or_flight_type() -> None:
    source = FakeFlightSource(query=[flight("SK1415", 10)])

    result = FlightService(source).search("SK1415", DAY)

    assert flight_ids(result) == ["SK1415"]
    assert source.calls == [("query", ("flightId eq 'SK1415' and scheduled eq '261124'",))]


@pytest.mark.parametrize("typed", ["sk 1415", " SK1415 ", "sk1415", "Sk 14 15"])
def test_search_normalises_the_flight_id(typed: str) -> None:
    source = FakeFlightSource()

    FlightService(source).search(typed, DAY)

    assert source.calls == [("query", ("flightId eq 'SK1415' and scheduled eq '261124'",))]


def test_search_adds_the_airport_only_when_given() -> None:
    source = FakeFlightSource()

    FlightService(source).search("SK1415", DAY, airport="got")

    assert source.calls == [
        ("query", ("flightId eq 'SK1415' and scheduled eq '261124' and airport eq 'GOT'",))
    ]


def test_search_not_found_is_an_empty_list() -> None:
    assert FlightService(FakeFlightSource()).search("SK1", DAY) == []


def test_search_returns_every_match_sorted() -> None:
    arrival = flight("SK1415", 20)
    departure = flight("SK1415", 8, Direction.DEPARTURE)
    source = FakeFlightSource(query=[arrival, departure])

    assert FlightService(source).search("SK1415", DAY) == [departure, arrival]


@pytest.mark.parametrize("bad", ["", "   ", "SK1' or airport eq 'ARN", "SK-14", "SK1415;"])
def test_search_rejects_ids_that_are_not_letters_and_digits_without_calling(bad: str) -> None:
    source = FakeFlightSource()

    with pytest.raises(BadQueryError, match="letters and digits"):
        FlightService(source).search(bad, DAY)

    assert source.call_count == 0


@pytest.mark.parametrize("bad", ["", "AR", "ARNX", "A'N", "12A"])
def test_search_rejects_a_malformed_airport_without_calling(bad: str) -> None:
    source = FakeFlightSource()

    with pytest.raises(BadQueryError, match="IATA"):
        FlightService(source).search("SK1", DAY, airport=bad)

    assert source.call_count == 0


# --- presets ------------------------------------------------------------------------------


def test_presets_cover_departures_arrivals_single_flight_and_status() -> None:
    presets = odata_presets("ARN", DAY)

    assert [p.label for p in presets] == [
        "Departures from ARN on 2026-11-24",
        "Arrivals at ARN on 2026-11-24",
        "One flight at ARN on 2026-11-24",
        "Cancelled flights at ARN on 2026-11-24",
    ]
    assert [p.needs_flight_id for p in presets] == [False, False, True, False]


def test_preset_filters_are_built_for_the_airport_and_day() -> None:
    departures, arrivals, single, cancelled = odata_presets("vby", date(2027, 1, 5))

    assert departures.build() == "airport eq 'VBY' and scheduled eq '270105' and flightType eq 'D'"
    assert arrivals.build() == "airport eq 'VBY' and scheduled eq '270105' and flightType eq 'A'"
    assert (
        single.build("sk 7") == "airport eq 'VBY' and scheduled eq '270105' and flightId eq 'SK7'"
    )
    assert (
        cancelled.build() == "airport eq 'VBY' and scheduled eq '270105' and flightStatus eq 'CAN'"
    )


@pytest.mark.parametrize("bad", [None, "", "SK1' or 'x"])
def test_single_flight_preset_needs_a_valid_flight_id(bad: str | None) -> None:
    single = odata_presets("ARN", DAY)[2]

    with pytest.raises(BadQueryError):
        single.build(bad)


def test_presets_reject_a_malformed_airport() -> None:
    with pytest.raises(BadQueryError, match="IATA"):
        odata_presets("AR'N", DAY)


def test_a_preset_runs_through_the_query_endpoint() -> None:
    source = FakeFlightSource(query=[flight("SK1", 5)])
    preset: ODataPreset = odata_presets("ARN", DAY)[0]

    result = FlightService(source).run_query(preset.build())

    assert flight_ids(result) == ["SK1"]
    assert source.calls == [("query", (preset.build(),))]


# --- passthrough --------------------------------------------------------------------------


def test_run_query_passes_the_filter_through_and_sorts() -> None:
    source = FakeFlightSource(query=[flight("B", 9), flight("A", 3)])

    result = FlightService(source).run_query("  airport eq 'ARN' or airport eq 'VBY'  ")

    assert flight_ids(result) == ["A", "B"]
    assert source.calls == [("query", ("airport eq 'ARN' or airport eq 'VBY'",))]


@pytest.mark.parametrize("empty", ["", "   ", "\t\n"])
def test_empty_filter_is_rejected_before_any_call(empty: str) -> None:
    source = FakeFlightSource()

    with pytest.raises(BadQueryError, match="Enter a filter"):
        FlightService(source).run_query(empty)

    assert source.call_count == 0


def test_rejected_filter_gets_a_helpful_hint() -> None:
    source = FakeFlightSource(error=BadQueryError("Swedavia rejected the filter (HTTP 400): bad"))

    with pytest.raises(BadQueryError) as raised:
        FlightService(source).run_query("airport eq")

    message = str(raised.value)
    assert "Swedavia rejected the filter (HTTP 400): bad" in message
    assert "flightType" in message
    assert "airport eq 'ARN'" in message


@pytest.mark.parametrize("error", [ApiUnavailableError("down"), QuotaExceededError("slow down")])
@pytest.mark.parametrize("call", ["arrivals", "departures", "search", "run_query"])
def test_other_api_errors_propagate_unchanged(error: ApiError, call: str) -> None:
    service = FlightService(FakeFlightSource(error=error))
    calls = {
        "arrivals": lambda: service.arrivals("ARN", DAY),
        "departures": lambda: service.departures("ARN", DAY),
        "search": lambda: service.search("SK1", DAY),
        "run_query": lambda: service.run_query("airport eq 'ARN'"),
    }

    with pytest.raises(type(error)) as raised:
        calls[call]()

    assert raised.value is error


@pytest.mark.parametrize("bad", ["", "AR", "A'N", "ARN/../x"])
@pytest.mark.parametrize("method", [FlightService.arrivals, FlightService.departures])
def test_lists_reject_a_malformed_airport_without_calling(
    method: Callable[[FlightService, str, date], list[Flight]], bad: str
) -> None:
    source = FakeFlightSource()

    with pytest.raises(BadQueryError, match="IATA"):
        method(FlightService(source), bad, DAY)

    assert source.call_count == 0


def test_lists_pass_a_normalised_airport_to_the_source() -> None:
    source = FakeFlightSource()

    FlightService(source).arrivals(" got ", DAY)

    assert source.calls == [("arrivals", ("GOT", DAY))]


# --- against the real offline source: the strings built here must be ones it understands ----

RECORDED_DAY = date(2026, 11, 24)


def test_search_works_against_the_offline_source() -> None:
    found = FlightService(OfflineFlightSource()).search("ay 808", RECORDED_DAY)

    assert flight_ids(found) == ["AY808"]


def test_supported_presets_work_against_the_offline_source() -> None:
    service = FlightService(OfflineFlightSource())
    departures, arrivals, single, _ = odata_presets("ARN", RECORDED_DAY)

    assert len(service.run_query(departures.build())) == 277
    assert len(service.run_query(arrivals.build())) == 289
    assert flight_ids(service.run_query(single.build("AY808"))) == ["AY808"]


def test_status_preset_offline_gives_a_message_that_does_not_contradict_itself() -> None:
    cancelled = odata_presets("ARN", RECORDED_DAY)[3]

    with pytest.raises(BadQueryError) as raised:
        FlightService(OfflineFlightSource()).run_query(cancelled.build())

    message = str(raised.value)
    offline_part, live_part = message.split(" Live API: ", 1)
    assert offline_part.startswith("Offline mode only supports")
    assert "flightStatus" not in offline_part
    assert "flightStatus" in live_part
    assert len(message) <= 280
