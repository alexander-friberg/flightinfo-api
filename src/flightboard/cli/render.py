"""The original app's flight card, as plain text. Pure functions: a `Flight` in, a string out."""

import re
from datetime import datetime

from flightboard.domain.airports import AIRPORTS, to_local
from flightboard.domain.models import Direction, Flight, HealthStatus, Scope
from flightboard.services.health import HeartbeatReport

MISSING = "N/A"
NO_TIME = "–"
RULE = "  " + "─" * 40


def render_flight(index: int, flight: Flight) -> str:
    """One card, numbered `index`, with labels and spacing as in the original."""
    own = _airport(AIRPORTS.get(flight.airport_iata or ""), flight.airport_iata)
    other = _airport(flight.other_airport_name, flight.other_airport_iata)
    origin, destination = (other, own) if flight.direction is Direction.ARRIVAL else (own, other)

    lines = [
        f"[{index}] → {flight.flight_id or MISSING}  |  {_airline(flight)}",
        f"  From  : {origin}",
        f"  To    : {destination}",
        f"  Status   : {flight.status or MISSING}",
        f"  Terminal : {flight.terminal or MISSING}    Gate: {flight.gate or MISSING}",
    ]
    if flight.direction is Direction.ARRIVAL:
        lines.append(f"  Baggage  : {flight.baggage_belt or MISSING}")
    lines += [
        f"  Sched : {_time(flight.times.scheduled)}",
        f"  Est   : {_time(flight.times.estimated)}",
        f"  Actual: {_time(flight.times.actual)}",
        f"  D/I     : {MISSING if flight.scope is Scope.UNKNOWN else flight.scope.value}",
        RULE,
    ]
    return "\n".join(lines)


def _airline(flight: Flight) -> str:
    name = flight.airline_name or MISSING
    return f"{name}  ({flight.airline_iata})" if flight.airline_iata else name


def _airport(name: str | None, code: str | None) -> str:
    """`Name (IATA)`. The API's name may already end in the code ("London LHR"); not doubled."""
    name = " ".join((name or "").split())
    if not code:
        return name or MISSING
    name = re.sub(rf"(^|\s+){re.escape(code)}$", "", name)
    return f"{name} ({code})" if name else f"({code})"


def _time(moment: datetime | None) -> str:
    if moment is None:
        return NO_TIME
    local = to_local(moment)
    return f"{moment:%H:%M} UTC → {local:%H:%M} {local.tzname()}"


def render_ping(number: int, status: HealthStatus) -> str:
    """One heartbeat line. Failures never show a time: a missing response has none (0.0), and a
    time next to an error message would read as if the API were up."""
    if not status.ok:
        return f"Ping {number}: FAILED – {status.message or 'no response'}"
    note = f" – {status.message}" if status.message else ""
    return f"Ping {number}: OK, {status.latency_ms:.0f} ms (HTTP {status.status_code}){note}"


def render_heartbeat_summary(report: HeartbeatReport) -> str:
    count = len(report.results)
    noun = "ping" if count == 1 else "pings"
    head = f"{count} {noun}: {report.successes} OK, {report.failures} failed."
    if report.min_ms is None or report.avg_ms is None or report.max_ms is None:
        return f"{head} No successful pings."
    return (
        f"{head} Latency min/avg/max: "
        f"{report.min_ms:.0f}/{report.avg_ms:.0f}/{report.max_ms:.0f} ms"
    )
