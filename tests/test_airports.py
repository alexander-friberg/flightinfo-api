from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from flightboard.domain.airports import AIRPORTS, resolve_airport, to_local

ORIGINAL_ORDER = ["ARN", "GOT", "BMA", "MMX", "LLA", "UME", "OSD", "VBY", "RNB", "KRN"]


def test_airports_follow_the_original_order_and_names() -> None:
    assert list(AIRPORTS) == ORIGINAL_ORDER
    assert AIRPORTS["ARN"] == "Stockholm Arlanda"
    assert AIRPORTS["GOT"] == "Göteborg Landvetter"
    assert AIRPORTS["OSD"] == "Östersund"


@pytest.mark.parametrize("code", ORIGINAL_ORDER)
@pytest.mark.parametrize("spelling", [str.upper, str.lower, str.title])
def test_every_iata_code_resolves_case_insensitively(
    code: str, spelling: Callable[[str], str]
) -> None:
    assert resolve_airport(spelling(code)) == code


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("arlanda", "ARN"),
        ("bromma", "BMA"),
        ("göteborg", "GOT"),
        ("goteborg", "GOT"),
        ("Göteborg", "GOT"),
        ("landvetter", "GOT"),
        ("gothenburg", "GOT"),
        ("malmö", "MMX"),
        ("malmo", "MMX"),
        ("luleå", "LLA"),
        ("lulea", "LLA"),
        ("umeå", "UME"),
        ("umea", "UME"),
        ("åre", "OSD"),
        ("are", "OSD"),
        ("östersund", "OSD"),
        ("ostersund", "OSD"),
        ("åre östersund", "OSD"),
        ("Visby", "VBY"),
        ("ronneby", "RNB"),
        ("kiruna", "KRN"),
        ("stockholm arlanda", "ARN"),
        ("Göteborg Landvetter", "GOT"),
    ],
)
def test_aliases_resolve_with_and_without_swedish_letters(raw: str, code: str) -> None:
    assert resolve_airport(raw) == code


@pytest.mark.parametrize(
    ("raw", "code"),
    [("  arn  ", "ARN"), ("\tvisby\n", "VBY"), (" göteborg ", "GOT"), ("åre   östersund", "OSD")],
)
def test_surrounding_whitespace_is_ignored(raw: str, code: str) -> None:
    assert resolve_airport(raw) == code


def test_airports_cannot_be_changed_by_callers() -> None:
    with pytest.raises(TypeError):
        AIRPORTS["XXX"] = "Nowhere"  # type: ignore[index]


@pytest.mark.parametrize("raw", ["", "   ", "XYZ", "LHR", "stockholm", "arland", "ar n"])
def test_unknown_input_resolves_to_none(raw: str) -> None:
    assert resolve_airport(raw) is None


@pytest.mark.parametrize(
    ("utc", "local", "zone"),
    [
        # Spring forward, last Sunday of March: 02:00 CET jumps to 03:00 CEST.
        (datetime(2026, 3, 29, 0, 59, tzinfo=UTC), "2026-03-29 01:59", "CET"),
        (datetime(2026, 3, 29, 1, 0, tzinfo=UTC), "2026-03-29 03:00", "CEST"),
        # Fall back, last Sunday of October: 03:00 CEST goes back to 02:00 CET.
        (datetime(2026, 10, 25, 0, 59, tzinfo=UTC), "2026-10-25 02:59", "CEST"),
        (datetime(2026, 10, 25, 1, 0, tzinfo=UTC), "2026-10-25 02:00", "CET"),
        # The flight card from the video: 16:25 UTC -> 17:25 CET.
        (datetime(2026, 1, 15, 16, 25, tzinfo=UTC), "2026-01-15 17:25", "CET"),
    ],
)
def test_to_local_converts_utc_to_stockholm_across_dst(
    utc: datetime, local: str, zone: str
) -> None:
    converted = to_local(utc)

    assert converted.strftime("%Y-%m-%d %H:%M") == local
    assert converted.tzname() == zone
    # Same instant. Not `converted == utc`: PEP 495 makes times in the repeated autumn hour
    # compare unequal across time zones, even when they are the same moment.
    assert converted.timestamp() == utc.timestamp()


def test_to_local_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        to_local(datetime(2026, 1, 15, 16, 25))
