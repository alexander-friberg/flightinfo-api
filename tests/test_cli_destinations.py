"""The destination overview offered after options 1 and 2, driven by scripted answers."""

import pytest

from flightboard.cli.destinations import FILTER_PROMPT, OFFER_PROMPT, offer_destination_overview
from flightboard.data.lookup import CityCountryLookup
from flightboard.domain.models import Direction, Flight
from tests.fakes import ScriptedConsole

LOOKUP = CityCountryLookup({"Oslo": "NORWAY", "London": "GREAT BRITAIN"})
FLIGHTS = [
    Flight(direction=Direction.DEPARTURE, other_airport_name=city)
    for city in ("Oslo", "London LHR", "Oslo", "Atlantis")
]


def run(answers: list[str], flights: list[Flight] = FLIGHTS) -> ScriptedConsole:
    script = ScriptedConsole(answers)
    offer_destination_overview(script.console, flights, LOOKUP)
    assert script.unused_answers == []
    return script


def test_prompts_are_worded_for_the_user() -> None:
    assert OFFER_PROMPT == "Show destination overview (cities, countries, flight counts)? [y/N]: "
    assert FILTER_PROMPT == "Filter? (country or city, Enter = none): "


@pytest.mark.parametrize("answer", ["", "n", "N", "no", "x"])
def test_anything_but_yes_declines_and_asks_nothing_more(answer: str) -> None:
    script = run([answer])

    assert script.prompts == [OFFER_PROMPT]
    assert script.lines == []


@pytest.mark.parametrize("answer", ["y", "Y", " yes "])
def test_yes_asks_for_a_filter_then_shows_the_table(answer: str) -> None:
    script = run([answer, ""])

    assert script.prompts == [OFFER_PROMPT, FILTER_PROMPT]
    header = next(i for i, line in enumerate(script.lines) if line.split()[:1] == ["City"])
    assert script.lines[header].split() == ["City", "Country", "Flights"]
    assert [line.split() for line in script.lines[header + 1 : header + 4]] == [
        ["Oslo", "NORWAY", "2"],
        ["Atlantis", "Unknown", "1"],
        ["London", "GREAT", "BRITAIN", "1"],
    ]
    assert script.lines[-1] == "Not in the statistics file (country unknown): Atlantis"


def test_the_filter_narrows_the_table() -> None:
    script = run(["y", "norway"])

    rows = [
        line.split() for line in script.lines if line.split()[-1:] and line.split()[-1].isdigit()
    ]
    assert rows == [["Oslo", "NORWAY", "2"]]
    assert not any("Atlantis" in line for line in script.lines)


def test_a_filter_that_matches_nothing_says_so_without_a_header() -> None:
    script = run(["y", "japan"])

    assert script.lines == ["No destinations found."]


def test_nothing_is_offered_for_an_empty_list() -> None:
    script = run([], flights=[])

    assert script.prompts == []
    assert script.lines == []
