"""The main menu: the original's six options plus the destination overview."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from flightboard.api.errors import ApiError
from flightboard.api.protocols import FlightSource
from flightboard.cli.destinations import run_destination_overview
from flightboard.cli.io import Console
from flightboard.cli.pager import page
from flightboard.cli.prompts import choose_airport, choose_date
from flightboard.cli.render import render_flight
from flightboard.data.lookup import CityCountryLookup
from flightboard.domain.models import Flight, HealthStatus
from flightboard.services.flights import FlightService, odata_presets
from flightboard.services.health import HeartbeatReport, heartbeat

TITLE = "Swedavia FlightInfo API v2 – Python client"
CHOICE_PROMPT = "Choose an option: "
FLIGHT_PROMPT = "Enter flight number (e.g. SK1415): "
FILTER_PROMPT = "Enter OData filter: "


@dataclass(frozen=True)
class App:
    """Everything the menu needs, passed in. Task 14 builds the real one; tests build fakes."""

    console: Console
    source: FlightSource
    lookup: CityCountryLookup
    today: Callable[[], date]
    sleep: Callable[[float], None]
    title: str = TITLE

    @property
    def flights(self) -> FlightService:
        return FlightService(self.source)


Handler = Callable[[App], None]


def run_menu(app: App) -> None:
    """Show the menu until the user quits. An `ApiError` in any option is one line, not a crash."""
    while True:
        app.console.write(app.title)
        for key, (label, _) in OPTIONS.items():
            app.console.write(f"{key}. {label}")
        app.console.write("q. Quit")
        choice = app.console.read(CHOICE_PROMPT).strip().lower()
        if choice == "q":
            app.console.write("Goodbye.")
            return
        option = OPTIONS.get(choice)
        if option is None:
            app.console.write("Unknown choice, try again.")
            continue
        _, handler = option
        try:
            handler(app)
        except ApiError as error:
            app.console.write(f"Error: {error}")


def _show(app: App, flights: list[Flight]) -> None:
    page(app.console, flights, render_flight)


def _arrivals(app: App) -> None:
    airport = choose_airport(app.console)
    _show(app, app.flights.arrivals(airport, choose_date(app.console, app.today())))


def _departures(app: App) -> None:
    airport = choose_airport(app.console)
    _show(app, app.flights.departures(airport, choose_date(app.console, app.today())))


def _search(app: App) -> None:
    flight_id = app.console.read(FLIGHT_PROMPT)
    _show(app, app.flights.search(flight_id, choose_date(app.console, app.today())))


def _odata(app: App) -> None:
    airport = choose_airport(app.console)
    presets = odata_presets(airport, choose_date(app.console, app.today()))
    for number, preset in enumerate(presets, start=1):
        app.console.write(f"  {number}. {preset.label}")
    custom = len(presets) + 1
    app.console.write(f"  {custom}. Type your own filter")
    # Compared as text: str.isdigit() also accepts "²", which int() then rejects.
    allowed = {str(number) for number in range(1, custom + 1)}
    while True:
        answer = app.console.read(f"Choose 1-{custom}: ").strip()
        if answer in allowed:
            break
        app.console.write(f"Type a number from 1 to {custom}.")
    if int(answer) == custom:
        odata_filter = app.console.read(FILTER_PROMPT)
    else:
        preset = presets[int(answer) - 1]
        flight_id = app.console.read(FLIGHT_PROMPT) if preset.needs_flight_id else None
        odata_filter = preset.build(flight_id)
    _show(app, app.flights.run_query(odata_filter))


def _health(app: App) -> None:
    report = heartbeat(app.source, sleep=app.sleep, on_result=lambda n, s: _ping(app, n, s))
    app.console.write(_summary(report))


def _ping(app: App, number: int, status: HealthStatus) -> None:
    if status.ok:
        note = f" – {status.message}" if status.message else ""
        app.console.write(
            f"Ping {number}: OK, {status.latency_ms:.0f} ms (HTTP {status.status_code}){note}"
        )
    else:
        # Failures never show a time: a missing response has none (latency 0.0), and a time
        # next to an error message would read as if the API were up.
        app.console.write(f"Ping {number}: FAILED – {status.message or 'no response'}")


def _summary(report: HeartbeatReport) -> str:
    head = f"{len(report.results)} pings: {report.successes} OK, {report.failures} failed."
    if report.min_ms is None or report.avg_ms is None or report.max_ms is None:
        return f"{head} No successful pings."
    return (
        f"{head} Latency min/avg/max: "
        f"{report.min_ms:.0f}/{report.avg_ms:.0f}/{report.max_ms:.0f} ms"
    )


def _demo(app: App) -> None:
    # shortcut: placeholder message, replaced by the full-auto demo in task 14.
    app.console.write("The full-auto demo isn't available yet.")


def _destinations(app: App) -> None:
    run_destination_overview(app.console, app.source, app.lookup, app.today())


OPTIONS: dict[str, tuple[str, Handler]] = {
    "1": ("Arrivals for an airport & date", _arrivals),
    "2": ("Departures for an airport & date", _departures),
    "3": ("Search a specific flight number", _search),
    "4": ("OData query (query endpoint)", _odata),
    "5": ("HeartBeat – API health check", _health),
    "6": ("Demonstrate all endpoints automatically", _demo),
    "7": ("Destination overview", _destinations),
}
