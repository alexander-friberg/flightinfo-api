"""Raw Swedavia JSON in, `Flight` objects out. Nothing past this module sees a dict.

Every field in the API is optional and missing ones are simply left out, so each lookup here
tolerates absence, empty strings and the wrong type, and turns them into `None`.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from flightboard.domain.models import Direction, Flight, FlightTimes, Scope

_EMPTY: Mapping[str, object] = {}


@dataclass(frozen=True)
class _Keys:
    """Where a direction keeps its fields: arrivals and departures mirror each other."""

    times: str
    other_name: str
    other_iata: str
    own_iata: str
    header: str


_KEYS = {
    Direction.ARRIVAL: _Keys(
        times="arrivalTime",
        other_name="departureAirportEnglish",
        other_iata="departureAirportIata",
        own_iata="arrivalAirportIata",
        header="to",
    ),
    Direction.DEPARTURE: _Keys(
        times="departureTime",
        other_name="arrivalAirportEnglish",
        other_iata="arrivalAirportIata",
        own_iata="departureAirportIata",
        header="from",
    ),
}


def is_valid_flight(raw: Mapping[str, object]) -> bool:
    """False for a ghost entry: no id, no other airport and no scheduled time (original rule)."""
    has_id = bool(raw.get("flightId"))
    has_origin = bool(raw.get("departureAirportEnglish") or raw.get("arrivalAirportEnglish"))
    times = _mapping(raw.get("arrivalTime") or raw.get("departureTime"))
    has_time = bool(times.get("scheduledUtc"))
    return has_id or has_origin or has_time


def parse_flights(payload: object, direction: Direction) -> list[Flight]:
    """Parse an arrivals or departures response (None, for a 204, gives an empty list)."""
    body = _mapping(payload)
    keys = _KEYS[direction]
    header_airport = _text(_mapping(body.get(keys.header)), keys.own_iata)
    return [_flight(raw, direction, header_airport) for raw in _items(body) if is_valid_flight(raw)]


def parse_query(payload: object) -> list[Flight]:
    """Parse a query response, where each item wraps an `arrival` or a `departure`.

    An item carrying both (not documented, never seen) yields both flights rather than losing one.
    """
    flights = []
    for item in _items(_mapping(payload)):
        for key, direction in (("arrival", Direction.ARRIVAL), ("departure", Direction.DEPARTURE)):
            raw = _mapping(item.get(key))
            if is_valid_flight(raw):
                flights.append(_flight(raw, direction, header_airport=None))
    return flights


def _flight(raw: Mapping[str, object], direction: Direction, header_airport: str | None) -> Flight:
    keys = _KEYS[direction]
    leg = _mapping(raw.get("flightLegIdentifier"))
    airline = _mapping(raw.get("airlineOperator"))
    place = _mapping(raw.get("locationAndStatus"))
    times = _mapping(raw.get(keys.times))
    indicator = raw.get("diIndicator")
    return Flight(
        direction=direction,
        flight_id=_text(raw, "flightId"),
        airline_name=_text(airline, "name"),
        airline_iata=_text(airline, "iata"),
        airport_iata=_text(leg, keys.own_iata) or header_airport,
        other_airport_name=_text(raw, keys.other_name),
        other_airport_iata=_text(leg, keys.other_iata),
        status=_text(place, "flightLegStatusEnglish"),
        terminal=_text(place, "terminal"),
        gate=_text(place, "gate"),
        baggage_belt=_text(_mapping(raw.get("baggage")), "baggageClaimUnit"),
        times=FlightTimes(
            scheduled=_time(times, "scheduledUtc"),
            estimated=_time(times, "estimatedUtc"),
            actual=_time(times, "actualUtc"),
        ),
        scope=Scope.from_indicator(indicator if isinstance(indicator, str) else None),
    )


def _items(body: Mapping[str, object]) -> list[Mapping[str, object]]:
    flights = body.get("flights")
    if not isinstance(flights, list):
        return []
    return [item for item in flights if isinstance(item, Mapping)]


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else _EMPTY


def _text(source: Mapping[str, object], key: str) -> str | None:
    value = source.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _time(source: Mapping[str, object], key: str) -> datetime | None:
    text = _text(source, key)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    # The API's `…Utc` fields are UTC; a value without an offset is read as UTC, not local time.
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
