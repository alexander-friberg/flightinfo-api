"""What the menu and the demo run on: every dependency, passed in."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from flightboard.api.protocols import FlightSource
from flightboard.cli.io import Console
from flightboard.data.lookup import CityCountryLookup
from flightboard.services.flights import FlightService

TITLE = "Swedavia FlightInfo API v2 – Python client"


@dataclass(frozen=True)
class App:
    """Everything the UI needs. `__main__` builds the real one; tests build one around fakes.

    `ping_count` is how many heartbeats option 5 sends; offline mode uses 1, because the sample
    source has no real latency to measure.
    """

    console: Console
    source: FlightSource
    lookup: CityCountryLookup
    today: Callable[[], date]
    sleep: Callable[[float], None]
    title: str = TITLE
    ping_count: int = 5

    @property
    def flights(self) -> FlightService:
        return FlightService(self.source)
