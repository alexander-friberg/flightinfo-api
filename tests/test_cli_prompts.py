from datetime import date

import pytest

from flightboard.cli.prompts import choose_airport, choose_date
from tests.fakes import ScriptedConsole

TODAY = date(2026, 11, 24)


# --- airport --------------------------------------------------------------------------------


def test_lists_the_ten_airports_in_the_originals_order_then_asks() -> None:
    script = ScriptedConsole(["arn"])

    choose_airport(script.console)

    assert script.lines[0] == "Available airports:"
    assert script.lines[1:] == [
        "  ARN – Stockholm Arlanda",
        "  GOT – Göteborg Landvetter",
        "  BMA – Stockholm Bromma",
        "  MMX – Malmö",
        "  LLA – Luleå",
        "  UME – Umeå",
        "  OSD – Östersund",
        "  VBY – Visby",
        "  RNB – Ronneby",
        "  KRN – Kiruna",
    ]
    assert script.prompts == ["Enter IATA code or city name (e.g. ARN or Visby): "]


@pytest.mark.parametrize(
    ("typed", "code"),
    [("arn", "ARN"), ("Visby", "VBY"), ("göteborg", "GOT"), ("  malmo ", "MMX"), ("BMA", "BMA")],
)
def test_accepts_codes_and_city_names(typed: str, code: str) -> None:
    assert choose_airport(ScriptedConsole([typed]).console) == code


def test_re_prompts_until_the_airport_is_known() -> None:
    script = ScriptedConsole(["xyz", "", "stockholm", "kiruna"])

    assert choose_airport(script.console) == "KRN"
    assert script.lines.count("Unknown airport, try again.") == 3
    assert len(script.prompts) == 4


# --- date -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("", TODAY),
        ("   ", TODAY),
        ("today", TODAY),
        ("TODAY", TODAY),
        ("now", TODAY),
        ("Now", TODAY),
        ("tomorrow", date(2026, 11, 25)),
        ("yesterday", date(2026, 11, 23)),
        ("2027-01-05", date(2027, 1, 5)),
        (" 2026-02-28 ", date(2026, 2, 28)),
    ],
)
def test_date_keywords_iso_dates_and_empty_input(typed: str, expected: date) -> None:
    script = ScriptedConsole([typed])

    assert choose_date(script.console, TODAY) == expected
    assert script.prompts == [
        "Enter date (YYYY-MM-DD / now / today / tomorrow / yesterday, Enter = today): "
    ]


def test_month_boundaries_follow_the_calendar() -> None:
    assert choose_date(ScriptedConsole(["tomorrow"]).console, date(2026, 12, 31)) == date(
        2027, 1, 1
    )


@pytest.mark.parametrize(
    "bad", ["20261124", "2026-1-5", "2026-02-30", "next week", "idag", "24/11"]
)
def test_re_prompts_on_anything_else(bad: str) -> None:
    script = ScriptedConsole([bad, "today"])

    assert choose_date(script.console, TODAY) == TODAY
    assert script.lines == ["Unknown date, try again."]
