"""Typed flight data. Pure values: no I/O, and every API field may be missing."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class Direction(Enum):
    """Values are the API's `flightType` codes, so they can go straight into an OData filter."""

    ARRIVAL = "A"
    DEPARTURE = "D"


class Scope(Enum):
    """The API's `diIndicator`: domestic, international or Schengen."""

    DOMESTIC = "D"
    INTERNATIONAL = "I"
    SCHENGEN = "S"
    UNKNOWN = "?"

    @classmethod
    def from_indicator(cls, indicator: str | None) -> "Scope":
        try:
            return cls((indicator or "").strip().upper())
        except ValueError:
            return cls.UNKNOWN


@dataclass(frozen=True)
class FlightTimes:
    """Scheduled, estimated and actual times, always timezone-aware UTC."""

    scheduled: datetime | None = None
    estimated: datetime | None = None
    actual: datetime | None = None

    def __post_init__(self) -> None:
        for name in ("scheduled", "estimated", "actual"):
            value: datetime | None = getattr(self, name)
            if value is None:
                continue
            if value.utcoffset() is None:
                raise ValueError(f"FlightTimes.{name} must be timezone-aware, got {value!r}")
            # Frozen dataclass: normalising has to go through object.__setattr__.
            object.__setattr__(self, name, value.astimezone(UTC))


@dataclass(frozen=True)
class Flight:
    """One arrival or departure at a Swedavia airport.

    `airport_iata` is the Swedavia airport the record belongs to; `other_airport_*` is the
    origin for an arrival and the destination for a departure.
    """

    direction: Direction
    flight_id: str | None = None
    airline_name: str | None = None
    airline_iata: str | None = None
    airport_iata: str | None = None
    other_airport_name: str | None = None
    other_airport_iata: str | None = None
    status: str | None = None
    terminal: str | None = None
    gate: str | None = None
    baggage_belt: str | None = None
    times: FlightTimes = field(default_factory=FlightTimes)
    scope: Scope = Scope.UNKNOWN


@dataclass(frozen=True)
class HealthStatus:
    """One heartbeat result. `status_code` is None when no HTTP response arrived."""

    ok: bool
    status_code: int | None
    latency_ms: float
    message: str | None = None
