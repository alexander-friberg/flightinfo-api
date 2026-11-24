"""Menu options 1–4 over a `FlightSource` (a service class plus OData presets): no terminal,
no HTTP."""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime

from flightboard.api.errors import BadQueryError
from flightboard.api.protocols import FlightSource
from flightboard.domain.models import Flight

# Worded for the live API, so it stays true after an offline source's own explanation.
QUERY_HINT = (
    "Live API: airport, flightType (A/D), scheduled (YYMMDD), estimated, flightStatus, flightId; "
    "eq ne gt ge lt le, and, or. E.g. airport eq 'ARN' and flightType eq 'D'"
)
_LAST = datetime.max.replace(tzinfo=UTC)

_FLIGHT_ID = re.compile(r"[A-Z0-9]+")
_IATA = re.compile(r"[A-Z]{3}")


@dataclass(frozen=True)
class ODataPreset:
    """A ready-made query. `template` may contain `{flight_id}`, filled in by `build`."""

    label: str
    template: str

    @property
    def needs_flight_id(self) -> bool:
        return "{flight_id}" in self.template

    def build(self, flight_id: str | None = None) -> str:
        """The filter string. `flight_id` is required when `needs_flight_id`, ignored otherwise."""
        if not self.needs_flight_id:
            return self.template
        return self.template.format(flight_id=_flight_id(flight_id or ""))


def odata_presets(airport: str, day: date) -> list[ODataPreset]:
    """The preset queries for one airport and day, in the order the menu shows them."""
    code = _airport(airport)
    base = f"airport eq '{code}' and scheduled eq '{_scheduled(day)}'"
    when = f"{code} on {day.isoformat()}"
    return [
        ODataPreset(f"Departures from {when}", f"{base} and flightType eq 'D'"),
        ODataPreset(f"Arrivals at {when}", f"{base} and flightType eq 'A'"),
        ODataPreset(f"One flight at {when}", f"{base} and flightId eq '{{flight_id}}'"),
        ODataPreset(f"Cancelled flights at {when}", f"{base} and flightStatus eq 'CAN'"),
    ]


class FlightService:
    """Arrivals, departures, flight search and OData queries, sorted for display."""

    def __init__(self, source: FlightSource) -> None:
        self._source = source

    def arrivals(self, airport: str, day: date) -> list[Flight]:
        return _sorted(self._source.arrivals(_airport(airport), day))

    def departures(self, airport: str, day: date) -> list[Flight]:
        return _sorted(self._source.departures(_airport(airport), day))

    def search(self, flight_id: str, day: date, airport: str | None = None) -> list[Flight]:
        """One query for the flight on that Swedish local day; both directions match."""
        odata_filter = f"flightId eq '{_flight_id(flight_id)}' and scheduled eq '{_scheduled(day)}'"
        if airport is not None:
            odata_filter += f" and airport eq '{_airport(airport)}'"
        return _sorted(self._source.query(odata_filter))

    def run_query(self, odata_filter: str) -> list[Flight]:
        """Run a user-written filter. Empty input never reaches the API."""
        cleaned = odata_filter.strip()
        if not cleaned:
            raise BadQueryError(f"Enter a filter. {QUERY_HINT}")
        try:
            return _sorted(self._source.query(cleaned))
        except BadQueryError as error:
            raise BadQueryError(f"{error} {QUERY_HINT}") from None


def _sorted(flights: list[Flight]) -> list[Flight]:
    """By scheduled time; flights without one go last; ties by flight id."""
    return sorted(flights, key=lambda f: (f.times.scheduled or _LAST, f.flight_id or ""))


def _scheduled(day: date) -> str:
    return f"{day:%y%m%d}"


def _flight_id(raw: str) -> str:
    # Validated, not escaped: a quote in user input must never change the meaning of a filter.
    normalised = "".join(raw.split()).upper()
    if not _FLIGHT_ID.fullmatch(normalised):
        raise BadQueryError(
            f"A flight number has only letters and digits, e.g. SK1415 (got {raw!r})."
        )
    return normalised


def _airport(raw: str) -> str:
    code = raw.strip().upper()
    if not _IATA.fullmatch(code):
        raise BadQueryError(f"An airport must be a three-letter IATA code, e.g. ARN (got {raw!r}).")
    return code
