"""Option 7, the destination overview, driven by scripted answers against fake data."""

from datetime import date

import pytest

from flightboard.cli.destinations import WHICH_PROMPT, run_destination_overview
from flightboard.data.lookup import CityCountryLookup
from flightboard.domain.models import Direction, Flight
from tests.fakes import FakeFlightSource, ScriptedConsole

TODAY = date(2026, 11, 24)
LOOKUP = CityCountryLookup({"Oslo": "NORWAY", "London": "GREAT BRITAIN"})


def source() -> FakeFlightSource:
    def arriving(city: str) -> Flight:
        return Flight(direction=Direction.ARRIVAL, other_airport_name=city)

    def departing(city: str) -> Flight:
        return Flight(direction=Direction.DEPARTURE, other_airport_name=city)

    return FakeFlightSource(
        arrivals=[arriving("Oslo"), arriving("London LHR"), arriving("Oslo")],
        departures=[departing("Atlantis"), departing("Oslo")],
    )


def run(
    answers: list[str], fake: FakeFlightSource | None = None
) -> tuple[ScriptedConsole, FakeFlightSource]:
    script = ScriptedConsole(answers)
    fake = fake or source()
    run_destination_overview(script.console, fake, LOOKUP, TODAY)
    assert script.unused_answers == []
    return script, fake


def table(script: ScriptedConsole) -> list[list[str]]:
    rows = [line.split() for line in script.lines]
    return [r for r in rows if len(r) == 3 and r[2].isdigit()]


def test_asks_in_the_originals_order() -> None:
    script, _ = run(["arn", "", "", "1"])

    assert script.prompts == [
        "Enter IATA code or city name (e.g. ARN or Visby): ",
        "Enter date (YYYY-MM-DD / now / today / tomorrow / yesterday, Enter = today): ",
        "Filter? (country or city, Enter = none): ",
        WHICH_PROMPT,
    ]
    assert WHICH_PROMPT == "Show 1 arrivals / 2 departures / 3 both: "


def test_shows_a_city_country_count_table_with_a_header() -> None:
    script, fake = run(["arn", "", "", "1"])

    assert fake.calls == [("arrivals", ("ARN", TODAY))]
    assert any(line.split() == ["City", "Country", "Flights"] for line in script.lines)
    header = next(i for i, line in enumerate(script.lines) if line.split()[:1] == ["City"])
    assert [line.split() for line in script.lines[header + 1 : header + 3]] == [
        ["Oslo", "NORWAY", "2"],
        ["London", "GREAT", "BRITAIN", "1"],
    ]


def test_both_merges_and_unmatched_cities_are_listed_after_the_table() -> None:
    script, fake = run(["arn", "", "", "3"])

    assert [name for name, _ in fake.calls] == ["arrivals", "departures"]
    assert table(script)[0] == ["Oslo", "NORWAY", "3"]
    assert script.lines[-1] == "Not in the statistics file (country unknown): Atlantis"


def test_the_filter_is_passed_through() -> None:
    script, _ = run(["arn", "", "norway", "3"])

    assert table(script) == [["Oslo", "NORWAY", "3"]]
    assert not any("Atlantis" in line for line in script.lines)


@pytest.mark.parametrize("bad", ["4", "0", "both", ""])
def test_the_1_to_3_choice_re_prompts_on_anything_else(bad: str) -> None:
    script, fake = run(["arn", "", "", bad, "2"])

    assert "Type 1, 2 or 3." in script.lines
    assert script.prompts.count(WHICH_PROMPT) == 2
    assert [name for name, _ in fake.calls] == ["departures"]


def test_nothing_found_says_so() -> None:
    script, _ = run(["arn", "", "", "1"], FakeFlightSource())

    assert "No destinations found." in script.lines


def test_no_table_header_when_there_is_nothing_to_show() -> None:
    script, _ = run(["arn", "", "", "1"], FakeFlightSource())

    assert not any(line.split()[:1] == ["City"] for line in script.lines)
