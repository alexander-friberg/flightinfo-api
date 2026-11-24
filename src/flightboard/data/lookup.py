"""City → country, from Swedavia's statistics file, matched against the API's city names."""

import json
import re
from collections.abc import Callable, Mapping
from importlib.resources import files

from flightboard.domain.airports import fold

# The API's English names that differ from the statistics file (research.md, "City spelling").
# Secondary airports map to the city the statistics file uses for them.
CITY_ALIASES: Mapping[str, str] = {
    "Addis Abeba": "Addis Ababa",
    "Geneva": "Geneve",
    "Vaasa": "Vasa",
    "Sal": "Sal Island",
    "Sundsvall": "Sundsvall Härnösand",
    "Hemavan Tärnaby": "Hemavan",
    "Åre Östersund": "Östersund",
    "Munich": "München",
    "Malta": "Valetta",
    "Bergamo": "Milan",
    "Charleroi": "Brussels",
}

# "London LHR", "Paris CDG": cities with several airports get the airport code appended.
_AIRPORT_SUFFIX = re.compile(r"^(.*\S)\s+[A-Z]{3}$")


def read_city_country() -> str:
    """The shipped `city_country.json`, read from inside the package."""
    return files("flightboard.data").joinpath("city_country.json").read_text(encoding="utf-8")


def load_lookup(loader: Callable[[], str] = read_city_country) -> "CityCountryLookup":
    mapping = json.loads(loader())
    if not isinstance(mapping, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()
    ):
        raise ValueError("city_country.json must be a JSON object of city name -> country name")
    return CityCountryLookup(mapping)


class CityCountryLookup:
    """Finds the country for a city name as the API writes it.

    Matching ignores case, extra whitespace and accents (`Göteborg` = `goteborg`), strips a
    trailing airport code, and applies `aliases` for known spelling differences.
    """

    def __init__(
        self, mapping: Mapping[str, str], aliases: Mapping[str, str] = CITY_ALIASES
    ) -> None:
        self._countries = {fold(city): country for city, country in mapping.items()}
        self._aliases = {fold(api): fold(stats) for api, stats in aliases.items()}

    def city_name(self, api_city: str) -> str:
        """The city without a trailing airport code: `London LHR` -> `London`."""
        cleaned = " ".join(api_city.split())
        match = _AIRPORT_SUFFIX.fullmatch(cleaned)
        return match.group(1) if match else cleaned

    def country_for(self, api_city: str) -> str | None:
        """The country, or None when the city isn't in the statistics (or is "Unknown")."""
        key = fold(self.city_name(api_city))
        if not key or key == "unknown":
            return None
        return self._countries.get(self._aliases.get(key, key))
