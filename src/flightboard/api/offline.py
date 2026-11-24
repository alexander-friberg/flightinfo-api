"""A `FlightSource` that answers from recorded sample data: no network, no key, no quota."""

import json
import re
from collections.abc import Callable
from datetime import date, datetime
from importlib.resources import files

from flightboard.api.errors import BadQueryError
from flightboard.api.parsing import parse_flights
from flightboard.domain.airports import AIRPORTS
from flightboard.domain.models import Direction, Flight, HealthStatus

SAMPLE_AIRPORT = "ARN"
SAMPLE_DAY = date(2026, 11, 24)
ARRIVALS_FILE = f"arrivals_{SAMPLE_AIRPORT}.json"
DEPARTURES_FILE = f"departures_{SAMPLE_AIRPORT}.json"

SUPPORTED = (
    "Offline mode only supports eq filters on flightId, airport, flightType and scheduled, "
    "joined with 'and'."
)

# OData keywords are matched case-insensitively, like the field values below.
_CLAUSE = re.compile(r"(\w+)\s+eq\s+'([^']*)'", re.IGNORECASE)
_AND = re.compile(r"\s+and\s+", re.IGNORECASE)
_SCHEDULED = {re.compile(r"\d{6}"): "%y%m%d", re.compile(r"\d{4}-\d{2}-\d{2}"): "%Y-%m-%d"}
_IATA = re.compile(r"[A-Za-z]{3}")


def _any_flight(flight: Flight) -> bool:
    return True


def read_sample(name: str) -> str:
    """Read a sample file shipped inside the package (works when installed, not only in git)."""
    return files("flightboard.data").joinpath("samples", name).read_text(encoding="utf-8")


class OfflineFlightSource:
    """Serves one recorded day at ARN for every airport and day asked for.

    The flights keep their real airport (ARN) rather than pretending to be somewhere else;
    `label` says what the data is, for the menu header. Queries follow the same rule as the
    lists: `airport` and `scheduled` are validated but match the whole sample, so a search for
    today still finds the recorded flights.
    """

    label = (
        f"Offline sample data: {AIRPORTS[SAMPLE_AIRPORT]}, "
        f"{SAMPLE_DAY:%d %b %Y} (recorded), shown for any airport and date"
    )

    def __init__(self, loader: Callable[[str], str] = read_sample) -> None:
        self._arrivals = parse_flights(json.loads(loader(ARRIVALS_FILE)), Direction.ARRIVAL)
        self._departures = parse_flights(json.loads(loader(DEPARTURES_FILE)), Direction.DEPARTURE)

    def arrivals(self, airport: str, day: date) -> list[Flight]:
        return list(self._arrivals)

    def departures(self, airport: str, day: date) -> list[Flight]:
        return list(self._departures)

    def query(self, odata_filter: str) -> list[Flight]:
        conditions = _parse_filter(odata_filter)
        return [
            flight
            for flight in self._arrivals + self._departures
            if all(test(flight) for test in conditions)
        ]

    def health(self) -> HealthStatus:
        return HealthStatus(True, 200, 0.0, "Offline mode: sample data, no network used.")


def _parse_filter(odata_filter: str) -> list[Callable[[Flight], bool]]:
    clauses = _AND.split(odata_filter.strip())
    conditions = []
    for clause in clauses:
        match = _CLAUSE.fullmatch(clause.strip())
        if match is None:
            raise BadQueryError(SUPPORTED)
        conditions.append(_condition(match.group(1), match.group(2)))
    return conditions


def _condition(field: str, value: str) -> Callable[[Flight], bool]:
    value = value.strip()
    if field == "flightId" and value:
        wanted = "".join(value.split()).upper()
        return lambda f: (f.flight_id or "").upper() == wanted
    if field == "flightType" and value.upper() in ("A", "D"):
        direction = Direction(value.upper())
        return lambda f: f.direction is direction
    if field == "airport" and _IATA.fullmatch(value):
        return _any_flight
    if field == "scheduled" and _is_scheduled_date(value):
        return _any_flight
    raise BadQueryError(SUPPORTED)


def _is_scheduled_date(value: str) -> bool:
    """`scheduled` is a Swedish local date, written YYMMDD or YYYY-MM-DD (both verified live)."""
    for shape, pattern in _SCHEDULED.items():
        if shape.fullmatch(value):
            try:
                datetime.strptime(value, pattern)
            except ValueError:
                return False
            return True
    return False
