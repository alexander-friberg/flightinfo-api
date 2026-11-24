"""Remembers recent answers for a short while, so repeating a view doesn't spend quota."""

import time
from collections.abc import Callable
from datetime import date

from flightboard.api.protocols import FlightSource
from flightboard.domain.models import Flight, HealthStatus

_Key = tuple[str, tuple[object, ...]]


class CachingFlightSource:
    """A `FlightSource` that wraps another one and reuses its answers for `ttl_s` seconds.

    Only successful answers are kept; an error from the inner source passes straight through.
    `health()` always goes to the inner source. A TTL of 0 or less turns caching off.
    """

    def __init__(
        self,
        inner: FlightSource,
        ttl_s: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._inner = inner
        self._ttl_s = ttl_s
        self._clock = clock
        # shortcut: never evicts, which is fine for one interactive session's handful of keys;
        # bound it (e.g. drop expired entries on write) if the app ever runs unattended.
        self._entries: dict[_Key, tuple[float, list[Flight]]] = {}

    def arrivals(self, airport: str, day: date) -> list[Flight]:
        return self._cached(
            ("arrivals", (airport, day)), lambda: self._inner.arrivals(airport, day)
        )

    def departures(self, airport: str, day: date) -> list[Flight]:
        return self._cached(
            ("departures", (airport, day)), lambda: self._inner.departures(airport, day)
        )

    def query(self, odata_filter: str) -> list[Flight]:
        return self._cached(("query", (odata_filter,)), lambda: self._inner.query(odata_filter))

    def health(self) -> HealthStatus:
        return self._inner.health()

    def _cached(self, key: _Key, fetch: Callable[[], list[Flight]]) -> list[Flight]:
        if self._ttl_s <= 0:
            return fetch()
        now = self._clock()
        entry = self._entries.get(key)
        if entry is not None and now - entry[0] < self._ttl_s:
            return list(entry[1])
        flights = fetch()
        self._entries[key] = (now, list(flights))
        return list(flights)
