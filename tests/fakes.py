"""Hand-written test doubles. They behave like the real thing with canned data."""

from collections.abc import Iterable, Sequence
from datetime import date

from flightboard.api.errors import ApiError
from flightboard.cli.io import Console
from flightboard.domain.models import Flight, HealthStatus

HEALTHY = HealthStatus(ok=True, status_code=200, latency_ms=25.0)


class FakeFlightSource:
    """A `FlightSource` that returns canned flights and records every call.

    Set `error` to make every method (except `health`) raise it, like a failing API would.
    `health` is either one status returned every time, or a script played in order, where an
    `ApiError` entry is raised instead of returned.
    """

    def __init__(
        self,
        arrivals: list[Flight] | None = None,
        departures: list[Flight] | None = None,
        query: list[Flight] | None = None,
        health: HealthStatus | Sequence[HealthStatus | ApiError] = HEALTHY,
        error: ApiError | None = None,
    ) -> None:
        self._arrivals = list(arrivals or [])
        self._departures = list(departures or [])
        self._query = list(query or [])
        self._health = health if isinstance(health, HealthStatus) else tuple(health)
        self._health_calls = 0
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
        if isinstance(self._health, HealthStatus):
            return self._health
        assert self._health_calls < len(self._health), "health() called more often than scripted"
        step = self._health[self._health_calls]
        self._health_calls += 1
        if isinstance(step, ApiError):
            raise step
        return step

    def _answer(self, name: str, args: tuple[object, ...], flights: list[Flight]) -> list[Flight]:
        self.calls.append((name, args))
        if self.error is not None:
            raise self.error
        return list(flights)


class ScriptedConsole:
    """Builds a `Console` whose input is a fixed script and whose output is recorded."""

    def __init__(self, answers: Iterable[str] = ()) -> None:
        self._answers = list(answers)
        self.prompts: list[str] = []
        self.lines: list[str] = []
        self.console = Console(read=self._read, write=self.lines.append)

    @property
    def output(self) -> str:
        return "\n".join(self.lines)

    @property
    def unused_answers(self) -> list[str]:
        return list(self._answers)

    def _read(self, prompt: str) -> str:
        self.prompts.append(prompt)
        assert self._answers, f"the program asked {prompt!r} but the script has no answers left"
        return self._answers.pop(0)
