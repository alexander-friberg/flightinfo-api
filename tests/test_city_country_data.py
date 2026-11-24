"""The shipped city_country.json, built from Swedavia's 2025 statistics by
scripts/build_city_country.py. The original app's 263 cities / 59 countries came from an older
file and doesn't apply here (see research.md)."""

import json
from collections import defaultdict
from pathlib import Path

import pytest

from flightboard.data.lookup import load_lookup, read_city_country
from flightboard.domain.airports import fold

# What the build script reported for destinations-statistik-2025.xlsx.
CITIES = 345
COUNTRIES = 67
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def mapping() -> dict[str, str]:
    data = json.loads(read_city_country())
    assert isinstance(data, dict)
    return data


def test_counts_match_what_the_build_script_reported(mapping: dict[str, str]) -> None:
    assert len(mapping) == CITIES
    assert len(set(mapping.values())) == COUNTRIES


def test_no_empty_keys_or_values(mapping: dict[str, str]) -> None:
    assert all(city.strip() and country.strip() for city, country in mapping.items())


def test_no_subtotals_or_placeholders(mapping: dict[str, str]) -> None:
    text = " ".join([*mapping, *mapping.values()])
    assert "Summa" not in text
    assert "(tom)" not in text
    assert all(fold(entry) != "unknown" for entry in [*mapping, *mapping.values()])


def test_keys_are_sorted_so_rebuilds_are_byte_identical(mapping: dict[str, str]) -> None:
    assert list(mapping) == sorted(mapping)


@pytest.mark.parametrize(
    ("city", "country"),
    [
        ("Tirana", "ALBANIA"),
        ("Vienna", "AUSTRIA"),
        ("Visby", "SWEDEN"),
        ("London", "GREAT BRITAIN"),
    ],
)
def test_known_cities(mapping: dict[str, str], city: str, country: str) -> None:
    assert mapping[city] == country


def test_spellings_that_fold_together_agree_on_the_country(mapping: dict[str, str]) -> None:
    by_key: dict[str, set[str]] = defaultdict(set)
    for city, country in mapping.items():
        by_key[fold(city)].add(country)

    assert {key: c for key, c in by_key.items() if len(c) > 1} == {}


def test_every_recorded_api_city_resolves() -> None:
    """The recorded ARN fixtures: every city has a country, except the API's own "Unknown"."""
    lookup = load_lookup()
    cities = set()
    for name, key in [
        ("arrivals_ARN.json", "departureAirportEnglish"),
        ("departures_ARN.json", "arrivalAirportEnglish"),
    ]:
        payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        cities |= {f[key] for f in payload["flights"] if f.get(key)}

    missing = sorted(c for c in cities if lookup.country_for(c) is None)

    assert missing == ["Unknown"]


@pytest.mark.parametrize(
    ("api_city", "country"),
    [("Munich", "GERMANY"), ("Malta", "MALTA"), ("Charleroi", "BELGIUM"), ("Bergamo", "ITALY")],
)
def test_aliases_reach_real_entries_in_the_shipped_file(api_city: str, country: str) -> None:
    assert load_lookup().country_for(api_city) == country
