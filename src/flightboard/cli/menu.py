"""The main menu: the original's six options."""

from collections.abc import Callable

from flightboard.api.errors import ApiError
from flightboard.cli.app import App
from flightboard.cli.demo import run_demo
from flightboard.cli.destinations import offer_destination_overview
from flightboard.cli.pager import page
from flightboard.cli.prompts import choose_airport, choose_date
from flightboard.cli.render import render_flight, render_heartbeat_summary, render_ping
from flightboard.domain.models import Flight
from flightboard.services.flights import odata_presets
from flightboard.services.health import heartbeat

CHOICE_PROMPT = "Choose an option: "
FLIGHT_PROMPT = "Enter flight number (e.g. SK1415): "
FILTER_PROMPT = "Enter OData filter: "

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
    flights = app.flights.arrivals(airport, choose_date(app.console, app.today()))
    _show(app, flights)
    offer_destination_overview(app.console, flights, app.lookup)


def _departures(app: App) -> None:
    airport = choose_airport(app.console)
    flights = app.flights.departures(airport, choose_date(app.console, app.today()))
    _show(app, flights)
    offer_destination_overview(app.console, flights, app.lookup)


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
    report = heartbeat(
        app.source,
        count=app.ping_count,
        sleep=app.sleep,
        on_result=lambda n, s: app.console.write(render_ping(n, s)),
    )
    app.console.write(render_heartbeat_summary(report))


OPTIONS: dict[str, tuple[str, Handler]] = {
    "1": ("Arrivals for an airport & date", _arrivals),
    "2": ("Departures for an airport & date", _departures),
    "3": ("Search a specific flight number", _search),
    "4": ("OData query (query endpoint)", _odata),
    "5": ("HeartBeat – API health check", _health),
    "6": ("Demonstrate all endpoints automatically", run_demo),
}
