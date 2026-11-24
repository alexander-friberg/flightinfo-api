"""The whole menu, driven by scripted answers against fake data. No network, no waiting."""

from datetime import UTC, date, datetime

import pytest

from flightboard.api.errors import ApiUnavailableError, BadQueryError, QuotaExceededError
from flightboard.cli.app import App
from flightboard.cli.menu import run_menu
from flightboard.data.lookup import CityCountryLookup
from flightboard.domain.models import Direction, Flight, FlightTimes, HealthStatus
from tests.fakes import FakeFlightSource, ScriptedConsole

TODAY = date(2026, 11, 24)
LOOKUP = CityCountryLookup({"Oslo": "NORWAY"})


def flight(flight_id: str, direction: Direction = Direction.ARRIVAL) -> Flight:
    return Flight(
        direction=direction,
        flight_id=flight_id,
        airport_iata="ARN",
        other_airport_name="Oslo",
        times=FlightTimes(scheduled=datetime(2026, 11, 24, 9, 0, tzinfo=UTC)),
    )


def run(
    answers: list[str], source: FakeFlightSource | None = None
) -> tuple[ScriptedConsole, FakeFlightSource, list[float]]:
    script = ScriptedConsole(answers)
    source = source or FakeFlightSource(
        arrivals=[flight("SK1")],
        departures=[flight("SK2", Direction.DEPARTURE)],
        query=[flight("AY808", Direction.DEPARTURE)],
    )
    sleeps: list[float] = []
    app = App(
        console=script.console,
        source=source,
        lookup=LOOKUP,
        today=lambda: TODAY,
        sleep=sleeps.append,
    )
    run_menu(app)
    assert script.unused_answers == [], "the menu stopped before using every scripted answer"
    return script, source, sleeps


# --- the menu itself ----------------------------------------------------------------------


def test_menu_shows_exactly_the_originals_six_options_in_english() -> None:
    script, _, _ = run(["q"])

    assert script.lines[:8] == [
        "Swedavia FlightInfo API v2 – Python client",
        "1. Arrivals for an airport & date",
        "2. Departures for an airport & date",
        "3. Search a specific flight number",
        "4. OData query (query endpoint)",
        "5. HeartBeat – API health check",
        "6. Demonstrate all endpoints automatically",
        "q. Quit",
    ]
    assert script.prompts == ["Choose an option: "]
    assert script.lines[-1] == "Goodbye."


def test_the_title_can_say_what_data_is_shown() -> None:
    script = ScriptedConsole(["q"])
    app = App(
        console=script.console,
        source=FakeFlightSource(),
        lookup=LOOKUP,
        today=lambda: TODAY,
        sleep=lambda _: None,
        title="Swedavia FlightInfo API v2 – OFFLINE sample data",
    )

    run_menu(app)

    assert script.lines[0] == "Swedavia FlightInfo API v2 – OFFLINE sample data"


@pytest.mark.parametrize("bad", ["8", "0", "x", "", " Q1"])
def test_invalid_choices_re_prompt(bad: str) -> None:
    script, source, _ = run([bad, "q"])

    assert "Unknown choice, try again." in script.lines
    assert script.prompts == ["Choose an option: ", "Choose an option: "]
    assert source.call_count == 0


def test_choices_ignore_case_and_spaces() -> None:
    script, _, _ = run([" Q "])

    assert script.lines[-1] == "Goodbye."


# --- options 1-3 ----------------------------------------------------------------------------


def test_option_1_shows_arrivals_for_the_chosen_airport_and_date() -> None:
    script, source, _ = run(["1", "visby", "tomorrow", "", "q"])

    assert source.calls == [("arrivals", ("VBY", date(2026, 11, 25)))]
    assert "[1] → SK1  |  N/A" in script.lines


def test_option_2_shows_departures() -> None:
    script, source, _ = run(["2", "arn", "", "", "q"])

    assert source.calls == [("departures", ("ARN", TODAY))]
    assert "[1] → SK2  |  N/A" in script.lines


def test_long_lists_are_paged() -> None:
    many = [flight(f"SK{i}") for i in range(60)]
    script, _, _ = run(["1", "arn", "", "q", "", "q"], FakeFlightSource(arrivals=many))

    assert "── Showing 50/60 ──  (10 left)" in script.lines
    assert not any(line.startswith("[51]") for line in script.lines)


def test_option_3_searches_for_a_flight_number_on_a_date() -> None:
    script, source, _ = run(["3", "ay 808", "2026-11-24", "q"])

    assert source.calls == [("query", ("flightId eq 'AY808' and scheduled eq '261124'",))]
    assert script.prompts[1] == "Enter flight number (e.g. SK1415): "
    assert "[1] → AY808  |  N/A" in script.lines


def test_option_3_with_no_match_says_so() -> None:
    script, _, _ = run(["3", "SK1", "", "q"], FakeFlightSource())

    assert "No flights found." in script.lines


# --- option 4 -------------------------------------------------------------------------------


def test_option_4_lists_the_presets_and_runs_one() -> None:
    script, source, _ = run(["4", "arn", "", "1", "q"])

    assert [line for line in script.lines if line.startswith("  ") and ". " in line[:6]] == [
        "  1. Departures from ARN on 2026-11-24",
        "  2. Arrivals at ARN on 2026-11-24",
        "  3. One flight at ARN on 2026-11-24",
        "  4. Cancelled flights at ARN on 2026-11-24",
        "  5. Type your own filter",
    ]
    assert source.calls == [
        ("query", ("airport eq 'ARN' and scheduled eq '261124' and flightType eq 'D'",))
    ]
    assert "[1] → AY808  |  N/A" in script.lines


def test_option_4_single_flight_preset_asks_for_the_flight_number() -> None:
    _, source, _ = run(["4", "arn", "", "3", "sk 7", "q"])

    assert source.calls == [
        ("query", ("airport eq 'ARN' and scheduled eq '261124' and flightId eq 'SK7'",))
    ]


def test_option_4_runs_a_custom_filter() -> None:
    script, source, _ = run(["4", "arn", "", "5", "flightType eq 'A'", "q"])

    assert script.prompts[-2] == "Enter OData filter: "
    assert source.calls == [("query", ("flightType eq 'A'",))]


def test_option_4_re_prompts_for_an_unknown_preset() -> None:
    script, source, _ = run(["4", "arn", "", "9", "x", "²", "2", "q"])

    assert script.lines.count("Type a number from 1 to 5.") == 3
    assert source.call_count == 1


# --- option 5 -------------------------------------------------------------------------------


def test_option_5_prints_each_ping_then_a_summary() -> None:
    source = FakeFlightSource(
        health=[
            HealthStatus(ok=True, status_code=200, latency_ms=40.0),
            HealthStatus(ok=False, status_code=503, latency_ms=12.0, message="HTTP 503"),
            QuotaExceededError("Too many requests"),
            HealthStatus(ok=True, status_code=200, latency_ms=20.0),
            HealthStatus(ok=True, status_code=200, latency_ms=30.0),
        ]
    )

    script, _, sleeps = run(["5", "q"], source)

    assert [line for line in script.lines if line.startswith("Ping")] == [
        "Ping 1: OK, 40 ms (HTTP 200)",
        "Ping 2: FAILED – HTTP 503",
        "Ping 3: FAILED – Too many requests",
        "Ping 4: OK, 20 ms (HTTP 200)",
        "Ping 5: OK, 30 ms (HTTP 200)",
    ]
    assert "5 pings: 3 OK, 2 failed. Latency min/avg/max: 20/30/40 ms" in script.lines
    assert sleeps == [2.0, 2.0, 2.0, 2.0]
    assert not any("0.0 ms" in line or " 0 ms" in line for line in script.lines)


def test_option_5_shows_the_message_of_a_successful_ping_when_there_is_one() -> None:
    offline = HealthStatus(ok=True, status_code=200, latency_ms=0.0, message="Offline mode")

    script, _, _ = run(["5", "q"], FakeFlightSource(health=offline))

    assert "Ping 1: OK, 0 ms (HTTP 200) – Offline mode" in script.lines


def test_option_5_summary_when_every_ping_fails() -> None:
    down = HealthStatus(ok=False, status_code=None, latency_ms=0.0, message="timed out")

    script, _, _ = run(["5", "q"], FakeFlightSource(health=down))

    assert "5 pings: 0 OK, 5 failed. No successful pings." in script.lines


# --- options 6 and 7 ------------------------------------------------------------------------


def test_option_6_runs_the_full_auto_demo() -> None:
    script, source, sleeps = run(["6", "q"])

    assert "=== Demo finished ===" in script.lines
    assert [name for name, _ in source.calls][:2] == ["arrivals", "departures"]
    assert sleeps[:4] == [2.5, 2.5, 2.5, 2.5]


def test_there_is_no_seventh_option() -> None:
    script, _, _ = run(["7", "q"])

    assert "Unknown choice, try again." in script.lines


@pytest.mark.parametrize(("option", "call"), [("1", "arrivals"), ("2", "departures")])
def test_options_1_and_2_offer_the_destination_overview_from_the_same_fetch(
    option: str, call: str
) -> None:
    script, source, _ = run([option, "arn", "", "y", "", "q"])

    assert "Show destination overview (cities, countries, flight counts)? [y/N]: " in script.prompts
    assert any(line.split() == ["Oslo", "NORWAY", "1"] for line in script.lines)
    assert [name for name, _ in source.calls] == [call]


def test_declining_the_overview_goes_back_to_the_menu() -> None:
    script, _, _ = run(["1", "arn", "", "n", "q"])

    assert not any(line.split()[:1] == ["City"] for line in script.lines)
    assert script.lines[-1] == "Goodbye."


def test_no_overview_is_offered_for_searches_and_queries() -> None:
    script, _, _ = run(["3", "AY808", "", "4", "arn", "", "1", "q"])

    assert not any("destination overview" in prompt for prompt in script.prompts)


# --- errors -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("option", "answers"),
    [
        ("1", ["arn", ""]),
        ("2", ["arn", ""]),
        ("3", ["SK1", ""]),
        ("4", ["arn", "", "1"]),
    ],
)
def test_an_api_error_is_one_friendly_line_and_the_menu_continues(
    option: str, answers: list[str]
) -> None:
    source = FakeFlightSource(error=ApiUnavailableError("Swedavia had a server error (HTTP 503)."))

    script, _, _ = run([option, *answers, "1", "arn", "", "q"], source)

    assert script.lines.count("Error: Swedavia had a server error (HTTP 503).") == 2
    assert script.lines[-1] == "Goodbye."


def test_bad_input_that_the_service_rejects_is_shown_as_an_error() -> None:
    script, source, _ = run(["3", "SK-1'", "", "q"])

    assert any(line.startswith("Error: A flight number has only letters") for line in script.lines)
    assert source.call_count == 0


def test_a_rejected_custom_filter_is_shown_with_its_hint() -> None:
    source = FakeFlightSource(error=BadQueryError("Swedavia rejected the filter (HTTP 400): bad"))

    script, _, _ = run(["4", "arn", "", "5", "airport eq", "q"], source)

    [error] = [line for line in script.lines if line.startswith("Error:")]
    assert "HTTP 400" in error and "flightType" in error
