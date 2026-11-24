"""Menu option 6: every endpoint once, with no input, using the same services as the menu."""

from collections.abc import Callable

from flightboard.api.errors import ApiError
from flightboard.cli.app import App
from flightboard.cli.render import render_flight, render_heartbeat_summary, render_ping
from flightboard.domain.models import Flight
from flightboard.services.flights import odata_presets
from flightboard.services.health import heartbeat

DEMO_AIRPORT = "ARN"
# A little over the query endpoint's one-call-per-2-s limit: steps 3 and 4 are both queries.
DEMO_PAUSE_S = 2.5
CARDS_PER_LIST = 3
DEMO_PINGS = 3
DEPARTURES_PRESET = 0  # odata_presets() order: departures, arrivals, one flight, cancelled


def run_demo(app: App) -> None:
    """Five steps with headers. A step that fails is reported and the demo moves on."""
    day = app.today()
    pings = min(DEMO_PINGS, app.ping_count)
    app.console.write(f"=== Full-auto demo: every endpoint at {DEMO_AIRPORT}, {day} ===")
    departures: list[Flight] = []

    def arrivals() -> None:
        _header(app, 1, f"Arrivals at {DEMO_AIRPORT} on {day}")
        _show(app, app.flights.arrivals(DEMO_AIRPORT, day))

    def departures_step() -> None:
        _header(app, 2, f"Departures from {DEMO_AIRPORT} on {day}")
        departures.extend(app.flights.departures(DEMO_AIRPORT, day))
        _show(app, departures)

    def search() -> None:
        flight_id = next((f.flight_id for f in departures if f.flight_id), None)
        if flight_id is None:
            _header(app, 3, "Search for a flight")
            app.console.write("Skipped: no departure to search for.")
            return
        _header(app, 3, f"Search for flight {flight_id} on {day}")
        _show(app, app.flights.search(flight_id, day))

    def odata() -> None:
        preset = odata_presets(DEMO_AIRPORT, day)[DEPARTURES_PRESET]
        _header(app, 4, f"OData query: {preset.label}")
        app.console.write(f"Filter: {preset.build()}")
        _show(app, app.flights.run_query(preset.build()))

    def health() -> None:
        _header(app, 5, f"HeartBeat ({pings} {'ping' if pings == 1 else 'pings'})")
        report = heartbeat(
            app.source,
            count=pings,
            sleep=app.sleep,
            on_result=lambda n, s: app.console.write(render_ping(n, s)),
        )
        app.console.write(render_heartbeat_summary(report))

    steps: list[Callable[[], None]] = [arrivals, departures_step, search, odata, health]
    for number, step in enumerate(steps, start=1):
        if number > 1:
            app.sleep(DEMO_PAUSE_S)
        try:
            step()
        except ApiError as error:
            app.console.write(f"Error: {error}")
    app.console.write("=== Demo finished ===")


def _header(app: App, number: int, text: str) -> None:
    app.console.write(f"--- {number}/5 {text} ---")


def _show(app: App, flights: list[Flight]) -> None:
    if not flights:
        app.console.write("No flights found.")
        return
    for index, flight in enumerate(flights[:CARDS_PER_LIST], start=1):
        app.console.write(render_flight(index, flight))
    if len(flights) > CARDS_PER_LIST:
        app.console.write(f"… and {len(flights) - CARDS_PER_LIST} more")
