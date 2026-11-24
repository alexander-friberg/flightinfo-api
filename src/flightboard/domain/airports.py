"""The ten Swedavia airports, how users may name them, and local time."""

import unicodedata
from collections.abc import Mapping
from datetime import datetime
from types import MappingProxyType
from zoneinfo import ZoneInfo

# Order and names as the original app lists them.
AIRPORTS: Mapping[str, str] = MappingProxyType(
    {
        "ARN": "Stockholm Arlanda",
        "GOT": "Göteborg Landvetter",
        "BMA": "Stockholm Bromma",
        "MMX": "Malmö",
        "LLA": "Luleå",
        "UME": "Umeå",
        "OSD": "Östersund",
        "VBY": "Visby",
        "RNB": "Ronneby",
        "KRN": "Kiruna",
    }
)

STOCKHOLM = ZoneInfo("Europe/Stockholm")

# Plain "stockholm" is left out on purpose: it could mean ARN or BMA.
_EXTRA_ALIASES = {
    "arlanda": "ARN",
    "bromma": "BMA",
    "göteborg": "GOT",
    "landvetter": "GOT",
    "gothenburg": "GOT",
    "åre": "OSD",
    "åre östersund": "OSD",
}


def _fold(text: str) -> str:
    """Lower-case, collapse whitespace and strip accents, so `Göteborg` matches `goteborg`."""
    decomposed = unicodedata.normalize("NFKD", " ".join(text.split()).casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


_ALIASES = {
    _fold(name): code
    for name, code in [*((n, c) for c, n in AIRPORTS.items()), *_EXTRA_ALIASES.items()]
}


def resolve_airport(raw: str) -> str | None:
    """Return the IATA code for a code, city or airport name, or None if it isn't one of ours."""
    code = raw.strip().upper()
    if code in AIRPORTS:
        return code
    return _ALIASES.get(_fold(raw))


def to_local(dt: datetime) -> datetime:
    """Convert an aware datetime to Swedish local time (CET/CEST)."""
    if dt.utcoffset() is None:
        raise ValueError(f"to_local needs a timezone-aware datetime, got {dt!r}")
    return dt.astimezone(STOCKHOLM)
