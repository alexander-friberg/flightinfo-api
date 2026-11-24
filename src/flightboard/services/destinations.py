"""The destination overview (the original's `destinationer.py`): cities, countries, counts."""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import Enum

from flightboard.api.protocols import FlightSource
from flightboard.data.lookup import CityCountryLookup
from flightboard.domain.airports import fold
from flightboard.domain.models import Flight
from flightboard.services.flights import FlightService

UNKNOWN = "Unknown"


class Which(Enum):
    """Which lists `destination_overview` fetches (values mirror the original's 1–3 answers)."""

    ARRIVALS = "1"
    DEPARTURES = "2"
    BOTH = "3"


@dataclass(frozen=True)
class DestinationRow:
    city: str
    country: str
    count: int


@dataclass(frozen=True)
class DestinationOverview:
    """Rows by count, most flights first. `unmatched`: cities missing from the statistics."""

    rows: tuple[DestinationRow, ...]
    unmatched: tuple[str, ...]


def destination_overview(
    source: FlightSource,
    lookup: CityCountryLookup,
    airport: str,
    day: date,
    which: Which,
    match: str | None = None,
) -> DestinationOverview:
    """Count the flights per other city; `match` keeps rows whose city or country contains it."""
    flights = FlightService(source)
    fetched = []
    if which in (Which.ARRIVALS, Which.BOTH):
        fetched += flights.arrivals(airport, day)
    if which in (Which.DEPARTURES, Which.BOTH):
        fetched += flights.departures(airport, day)

    return summarise_destinations(fetched, lookup, match)


def summarise_destinations(
    flights: Sequence[Flight], lookup: CityCountryLookup, match: str | None = None
) -> DestinationOverview:
    """Count flights the caller already has per city and country (pure: no API call)."""
    # Grouped by the folded name, so "Oslo" and "OSLO" are one row; the first spelling is shown.
    shown: dict[str, str] = {}
    counts: Counter[str] = Counter()
    for f in flights:
        city = lookup.city_name(f.other_airport_name or UNKNOWN)
        key = fold(city)
        shown.setdefault(key, city)
        counts[key] += 1
    rows = [
        DestinationRow(shown[key], lookup.country_for(shown[key]) or UNKNOWN, count)
        for key, count in counts.items()
    ]

    wanted = fold(match or "")
    if wanted:
        rows = [r for r in rows if wanted in fold(r.city) or wanted in fold(r.country)]

    rows.sort(key=lambda r: (-r.count, fold(r.city)))
    unmatched = tuple(
        sorted(
            (r.city for r in rows if r.country == UNKNOWN and fold(r.city) != fold(UNKNOWN)),
            key=fold,
        )
    )
    return DestinationOverview(tuple(rows), unmatched)
