"""The questions the menu asks: which airport, which date."""

import re
from datetime import date, timedelta

from flightboard.cli.io import Console
from flightboard.domain.airports import AIRPORTS, resolve_airport

AIRPORT_PROMPT = "Enter IATA code or city name (e.g. ARN or Visby): "
DATE_PROMPT = "Enter date (YYYY-MM-DD / now / today / tomorrow / yesterday, Enter = today): "

_DAY_OFFSETS = {"": 0, "now": 0, "today": 0, "tomorrow": 1, "yesterday": -1}
_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def choose_airport(console: Console) -> str:
    """List the ten airports, then ask until the answer is one of them. Returns the IATA code."""
    console.write("Available airports:")
    for listed, name in AIRPORTS.items():
        console.write(f"  {listed} – {name}")
    while True:
        code = resolve_airport(console.read(AIRPORT_PROMPT))
        if code is not None:
            return code
        console.write("Unknown airport, try again.")


def choose_date(console: Console, today: date) -> date:
    """Ask until the answer is a date. `today` comes from the caller's clock, never from here."""
    while True:
        day = _parse_date(console.read(DATE_PROMPT), today)
        if day is not None:
            return day
        console.write("Unknown date, try again.")


def _parse_date(raw: str, today: date) -> date | None:
    text = raw.strip().lower()
    if text in _DAY_OFFSETS:
        return today + timedelta(days=_DAY_OFFSETS[text])
    # Exact shape first: `date.fromisoformat` would also accept forms like "20261124".
    if not _ISO_DATE.fullmatch(text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None
