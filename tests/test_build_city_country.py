import pytest

from scripts.build_city_country import city_country_pairs

HEADER = [
    ("Trafikflöde",),
    ("Traffic by flight stage",),
    ("Antal ankommande ...",),
    ("Number of arriving ...",),
    ("Land", "Stad", "Rapporterande flygplats, Stad"),
    ("Country", "City", "Reporting airport, City"),
]


def build(rows: list[tuple[object, ...]]) -> dict[str, str]:
    return city_country_pairs(HEADER + rows)


def test_keeps_country_city_pairs_and_skips_the_six_header_rows() -> None:
    result = build(
        [
            ("", "", "", "", ""),
            ("ALBANIA", "Tirana", "Bromma Stockholm Airport", None, 9),
            ("ALBANIA", "Tirana", "Malmö Airport", 9767, 51643),
            ("AUSTRIA", "Vienna", "Stockholm Arlanda Airport", 1, 2),
        ]
    )

    assert result == {"Tirana": "ALBANIA", "Vienna": "AUSTRIA"}


@pytest.mark.parametrize(
    "row",
    [
        ("ALBANIA", "Tirana Summa", "", 1),
        ("ALBANIA Summa", "", "", 1),
        ("(tom)", "Somewhere", "Arlanda", 1),
        ("LATVIA", "(tom)", "Arlanda", 1),
        ("UNKNOWN", "Nowhere", "Arlanda", 1),
        (None, "Orphan", "Arlanda", 1),
        ("SPAIN", None, "Arlanda", 1),
        ("  ", "  ", "", None),
        ("SPAIN",),
    ],
)
def test_skips_subtotals_placeholders_and_blanks(row: tuple[object, ...]) -> None:
    assert build([row]) == {}


def test_strips_surrounding_whitespace() -> None:
    assert build([("  SWEDEN ", " Visby  ", "Arlanda", 1)]) == {"Visby": "SWEDEN"}


def test_keeps_zero_passenger_cities() -> None:
    assert build([("AUSTRIA", "LINZ", "Arlanda", 0)]) == {"LINZ": "AUSTRIA"}


def test_a_city_in_two_countries_is_an_error() -> None:
    with pytest.raises(ValueError, match="Springfield"):
        build([("USA", "Springfield", "", 1), ("CANADA", "Springfield", "", 1)])
