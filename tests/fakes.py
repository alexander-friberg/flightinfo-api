"""Hand-written test doubles. They behave like the real thing with canned data."""

from datetime import date

from flightboard.api.errors import ApiError
from flightboard.domain.models import Flight, HealthStatus

HEALTHY = HealthStatus(ok=True, status_code=200, latency_ms=25.0)


class FakeFlightSource:
    """A `FlightSource` that returns canned flights and records every call.

    Set `error` to make every method (except `health`) raise it, like a failing API would.
    """

    def __init__(
        self,
        arrivals: list[Flight] | None = None,
        departures: list[Flight] | None = None,
        query: list[Flight] | None = None,
        health: HealthStatus = HEALTHY,
        error: ApiError | None = None,
    ) -> None:
        self._arrivals = list(arrivals or [])
        self._departures = list(departures or [])
        self._query = list(query or [])
        self._health = health
        self.error = error
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def arrivals(self, airport: str, day: date) -> list[Flight]:
        return self._answer("arrivals", (airport, day), self._arrivals)

    def departures(self, airport: str, day: date) -> list[Flight]:
        return self._answer("departures", (airport, day), self._departures)

    def query(self, odata_filter: str) -> list[Flight]:
        return self._answer("query", (odata_filter,), self._query)

    def health(self) -> HealthStatus:
        self.calls.append(("health", ()))
        return self._health

    def _answer(self, name: str, args: tuple[object, ...], flights: list[Flight]) -> list[Flight]:
        self.calls.append((name, args))
        if self.error is not None:
            raise self.error
        return list(flights)
