from datetime import date
from typing import Protocol

from flightboard.domain.models import Flight, HealthStatus


class FlightSource(Protocol):
    """Anything that can supply flights: the real client, the cache, offline data, test fakes.

    `arrivals`, `departures` and `query` raise `ApiError` subclasses when the data can't be had.
    `health` reports HTTP and network problems in the returned `HealthStatus` instead of raising.
    """

    def arrivals(self, airport: str, day: date) -> list[Flight]: ...

    def departures(self, airport: str, day: date) -> list[Flight]: ...

    def query(self, odata_filter: str) -> list[Flight]: ...

    def health(self) -> HealthStatus: ...
