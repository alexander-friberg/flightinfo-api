import pytest

from flightboard.data.lookup import CityCountryLookup, load_lookup

MAPPING = {
    "Tirana": "ALBANIA",
    "ALICANTE": "SPAIN",
    "London": "GREAT BRITAIN",
    "Göteborg": "SWEDEN",
    "Addis Ababa": "ETHIOPIA",
    "Geneve": "SWITZERLAND",
    "Östersund": "SWEDEN",
}


@pytest.fixture
def lookup() -> CityCountryLookup:
    return CityCountryLookup(MAPPING)


@pytest.mark.parametrize(
    ("api_city", "country"),
    [
        ("Tirana", "ALBANIA"),
        ("tirana", "ALBANIA"),
        ("  Tirana ", "ALBANIA"),
        ("Alicante", "SPAIN"),
        ("Göteborg", "SWEDEN"),
        ("Goteborg", "SWEDEN"),
        ("GÖTEBORG", "SWEDEN"),
    ],
)
def test_normalises_case_whitespace_and_swedish_letters(
    lookup: CityCountryLookup, api_city: str, country: str
) -> None:
    assert lookup.country_for(api_city) == country


@pytest.mark.parametrize("api_city", ["London LHR", "London LGW", "London STN", "London"])
def test_strips_a_trailing_airport_code(lookup: CityCountryLookup, api_city: str) -> None:
    assert lookup.country_for(api_city) == "GREAT BRITAIN"


def test_city_name_strips_the_airport_code(lookup: CityCountryLookup) -> None:
    assert lookup.city_name("Paris CDG") == "Paris"
    assert lookup.city_name(" Bucharest  BBU ") == "Bucharest"
    assert lookup.city_name("Tirana") == "Tirana"
    assert lookup.city_name("Rome FCO X") == "Rome FCO X"


@pytest.mark.parametrize(
    ("api_city", "country"),
    [("Addis Abeba", "ETHIOPIA"), ("Geneva", "SWITZERLAND"), ("Åre Östersund", "SWEDEN")],
)
def test_known_spelling_differences_use_the_alias_table(
    lookup: CityCountryLookup, api_city: str, country: str
) -> None:
    assert lookup.country_for(api_city) == country


@pytest.mark.parametrize("api_city", ["Atlantis", "", "   ", "Unknown", "unknown"])
def test_missing_cities_have_no_country(lookup: CityCountryLookup, api_city: str) -> None:
    assert lookup.country_for(api_city) is None


def test_mapping_is_injected_and_copied() -> None:
    mapping = {"Tirana": "ALBANIA"}
    lookup = CityCountryLookup(mapping)

    mapping["Tirana"] = "CHANGED"

    assert lookup.country_for("Tirana") == "ALBANIA"


def test_aliases_can_be_injected() -> None:
    lookup = CityCountryLookup({"Vasa": "FINLAND"}, aliases={"Vaasa": "Vasa"})

    assert lookup.country_for("VAASA") == "FINLAND"


@pytest.mark.parametrize("text", ['["Tirana"]', '{"Tirana": 1}', '{"Tirana": null}', "3"])
def test_loading_a_malformed_file_fails_clearly(text: str) -> None:
    with pytest.raises(ValueError, match="city name -> country name"):
        load_lookup(lambda: text)


def test_loading_uses_the_injected_reader() -> None:
    lookup = load_lookup(lambda: '{"Tirana": "ALBANIA"}')

    assert lookup.country_for("tirana") == "ALBANIA"
