"""The full-auto demo, end to end against fake data with a recording sleep (no waiting)."""

from datetime import UTC, date, datetime

from flightboard.api.errors import ApiUnavailableError
from flightboard.cli.app import App
from flightboard.cli.demo import DEMO_PAUSE_S, run_demo
from flightboard.data.lookup import CityCountryLookup
from flightboard.domain.models import Direction, Flight, FlightTimes
from tests.fakes import FakeFlightSource, ScriptedConsole

TODAY = date(2026, 11, 24)


def flights(prefix: str, count: int, direction: Direction) -> list[Flight]:
    return [
        Flight(
            direction=direction,
            flight_id=f"{prefix}{i}",
            airport_iata="ARN",
            times=FlightTimes(scheduled=datetime(2026, 11, 24, 6 + i, 0, tzinfo=UTC)),
        )
        for i in range(1, count + 1)
    ]


def run(source: FakeFlightSource) -> tuple[ScriptedConsole, list[float]]:
    script = ScriptedConsole()
    sleeps: list[float] = []
    app = App(
        console=script.console,
        source=source,
        lookup=CityCountryLookup({}),
        today=lambda: TODAY,
        sleep=sleeps.append,
    )
    run_demo(app)
    return script, sleeps


def full_source() -> FakeFlightSource:
    return FakeFlightSource(
        arrivals=flights("AR", 5, Direction.ARRIVAL),
        departures=flights("DE", 2, Direction.DEPARTURE),
        query=flights("Q", 1, Direction.DEPARTURE),
    )


def test_runs_every_step_with_a_header_and_no_input() -> None:
    script, _ = run(full_source())

    headers = [line for line in script.lines if line.startswith("---")]
    assert headers == [
        "--- 1/5 Arrivals at ARN on 2026-11-24 ---",
        "--- 2/5 Departures from ARN on 2026-11-24 ---",
        "--- 3/5 Search for flight DE1 on 2026-11-24 ---",
        "--- 4/5 OData query: Departures from ARN on 2026-11-24 ---",
        "--- 5/5 HeartBeat (3 pings) ---",
    ]
    assert script.lines[0] == "=== Full-auto demo: every endpoint at ARN, 2026-11-24 ==="
    assert script.lines[-1] == "=== Demo finished ==="
    assert script.prompts == []


def test_uses_the_same_calls_as_the_menu() -> None:
    source = full_source()

    run(source)

    assert source.calls == [
        ("arrivals", ("ARN", TODAY)),
        ("departures", ("ARN", TODAY)),
        ("query", ("flightId eq 'DE1' and scheduled eq '261124'",)),
        ("query", ("airport eq 'ARN' and scheduled eq '261124' and flightType eq 'D'",)),
        ("health", ()),
        ("health", ()),
        ("health", ()),
    ]


def test_shows_a_few_cards_per_list_and_how_many_more() -> None:
    script, _ = run(full_source())

    assert "[3] → AR3  |  N/A" in script.lines
    assert not any(line.startswith("[4] → AR4") for line in script.lines)
    assert "… and 2 more" in script.lines
    assert "[2] → DE2  |  N/A" in script.lines
    assert "Ping 3: OK, 25 ms (HTTP 200)" in script.lines
    assert "3 pings: 3 OK, 0 failed. Latency min/avg/max: 25/25/25 ms" in script.lines


def test_pauses_at_least_two_seconds_between_steps() -> None:
    _, sleeps = run(full_source())

    assert DEMO_PAUSE_S >= 2.0
    # Four pauses between the five steps, then the heartbeat's own two 2-s intervals.
    assert sleeps == [DEMO_PAUSE_S] * 4 + [2.0, 2.0]


def test_a_failing_step_is_reported_and_the_demo_continues() -> None:
    source = FakeFlightSource(error=ApiUnavailableError("Swedavia had a server error (HTTP 503)."))

    script, _ = run(source)

    assert script.lines.count("Error: Swedavia had a server error (HTTP 503).") >= 3
    assert "--- 5/5 HeartBeat (3 pings) ---" in script.lines
    assert script.lines[-1] == "=== Demo finished ==="


def test_search_is_skipped_when_there_are_no_departures() -> None:
    source = FakeFlightSource(arrivals=flights("AR", 1, Direction.ARRIVAL))

    script, _ = run(source)

    assert "--- 3/5 Search for a flight ---" in script.lines
    assert "Skipped: no departure to search for." in script.lines
    assert [name for name, _ in source.calls].count("query") == 1


def test_offline_app_pings_once() -> None:
    script = ScriptedConsole()
    app = App(
        console=script.console,
        source=FakeFlightSource(),
        lookup=CityCountryLookup({}),
        today=lambda: TODAY,
        sleep=lambda _: None,
        ping_count=1,
    )

    run_demo(app)

    assert "--- 5/5 HeartBeat (1 ping) ---" in script.lines
    assert "1 ping: 1 OK, 0 failed. Latency min/avg/max: 25/25/25 ms" in script.lines
