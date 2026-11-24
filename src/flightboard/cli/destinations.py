"""The destination overview (the original's `destinationer.py`), offered after options 1 and 2."""

from collections.abc import Sequence

from flightboard.cli.io import Console
from flightboard.cli.pager import page
from flightboard.data.lookup import CityCountryLookup
from flightboard.domain.models import Flight
from flightboard.services.destinations import DestinationRow, summarise_destinations

OFFER_PROMPT = "Show destination overview (cities, countries, flight counts)? [y/N]: "
FILTER_PROMPT = "Filter? (country or city, Enter = none): "
_ROW = "{city:<28} {country:<28} {count:>7}"


def offer_destination_overview(
    console: Console, flights: Sequence[Flight], lookup: CityCountryLookup
) -> None:
    """Offer the city | country | count table for the flights just listed (y/N, then a filter)."""
    if not flights:
        return
    if console.read(OFFER_PROMPT).strip().lower() not in ("y", "yes"):
        return
    match = console.read(FILTER_PROMPT).strip() or None
    overview = summarise_destinations(flights, lookup, match)

    if overview.rows:
        console.write(_ROW.format(city="City", country="Country", count="Flights"))
    page(console, overview.rows, _render_row, empty_message="No destinations found.")
    if overview.unmatched:
        console.write(
            "Not in the statistics file (country unknown): " + ", ".join(overview.unmatched)
        )


def _render_row(_: int, row: DestinationRow) -> str:
    return _ROW.format(city=row.city, country=row.country, count=row.count)
