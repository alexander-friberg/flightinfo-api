"""Menu option 7: the original's `destinationer.py` flow, asked in the same order."""

from datetime import date

from flightboard.api.protocols import FlightSource
from flightboard.cli.io import Console
from flightboard.cli.pager import page
from flightboard.cli.prompts import choose_airport, choose_date
from flightboard.data.lookup import CityCountryLookup
from flightboard.services.destinations import DestinationRow, Which, destination_overview

FILTER_PROMPT = "Filter? (country or city, Enter = none): "
WHICH_PROMPT = "Show 1 arrivals / 2 departures / 3 both: "
_ROW = "{city:<28} {country:<28} {count:>7}"


def run_destination_overview(
    console: Console, source: FlightSource, lookup: CityCountryLookup, today: date
) -> None:
    """Airport, date, optional filter, then 1/2/3; show the table and the unmatched cities."""
    airport = choose_airport(console)
    day = choose_date(console, today)
    match = console.read(FILTER_PROMPT).strip() or None
    which = _choose_which(console)

    overview = destination_overview(source, lookup, airport, day, which, match=match)

    if overview.rows:
        console.write(_ROW.format(city="City", country="Country", count="Flights"))
    page(console, overview.rows, _render_row, empty_message="No destinations found.")
    if overview.unmatched:
        console.write(
            "Not in the statistics file (country unknown): " + ", ".join(overview.unmatched)
        )


def _choose_which(console: Console) -> Which:
    while True:
        answer = console.read(WHICH_PROMPT).strip()
        if answer in ("1", "2", "3"):
            return Which(answer)
        console.write("Type 1, 2 or 3.")


def _render_row(_: int, row: DestinationRow) -> str:
    return _ROW.format(city=row.city, country=row.country, count=row.count)
