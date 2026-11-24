"""One-off tool: record real Swedavia responses as test fixtures.

Run with the key from `.env` (never pass it on the command line):

    uv run --env-file .env python -m scripts.record_fixtures

Makes 5 live calls, spaced out for the query endpoint's one-call-per-2-s limit.
"""

import json
import os
import sys
import time
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx

from flightboard.domain.airports import STOCKHOLM

BASE_URL = "https://api.swedavia.se/flightinfo/v2"
AIRPORT = "ARN"
PAUSE_S = 2.5
QUERY_COUNT = 1000
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
# The real token is a long base64 string next to the word "token", which secret scanners flag.
# The app never uses it (it is a change feed, not paging), so fixtures keep a placeholder.
CONTINUATION_PLACEHOLDER = "<continuation token removed from fixture>"


class KeyLeakError(Exception):
    """A saved fixture contains the API key."""


def record(
    client: httpx.Client,
    out_dir: Path,
    today: date,
    sleep: Callable[[float], None],
    key: str,
) -> dict[str, object]:
    """Fetch and save the four fixtures, plus an unsaved probe of the ISO date format."""
    headers = {"Ocp-Apim-Subscription-Key": key, "Accept": "application/json"}
    calls = 0

    # Any: raw, untyped JSON. This one-off tool saves it as-is; parsing is task 06's job.
    def get(path: str, params: dict[str, str] | None = None) -> Any:
        nonlocal calls
        if calls:
            sleep(PAUSE_S)
        calls += 1
        response = client.get(path, params=params, headers=headers)
        response.raise_for_status()
        return response.json() if response.content else None

    def save(name: str, payload: object) -> None:
        if isinstance(payload, dict) and payload.get("continuationtoken"):
            payload = {**payload, "continuationtoken": CONTINUATION_PLACEHOLDER}
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / name
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if key in path.read_text(encoding="utf-8"):
            path.unlink()
            raise KeyLeakError(f"{name} contained the API key; the file was deleted.")

    day = today.isoformat()
    save(f"arrivals_{AIRPORT}.json", get(f"/{AIRPORT}/arrivals/{day}"))
    departures = get(f"/{AIRPORT}/departures/{day}")
    save(f"departures_{AIRPORT}.json", departures)

    ids = [f["flightId"] for f in (departures or {}).get("flights") or [] if f.get("flightId")]
    if not ids:
        raise RuntimeError(
            f"No departures with a flight id at {AIRPORT} on {day}; nothing to search."
        )
    flight_id = ids[0]
    search = f"flightId eq '{flight_id}' and scheduled eq '{today:%y%m%d}'"
    save("query_sample.json", get("/query", {"filter": search, "count": str(QUERY_COUNT)}))

    iso_search = f"flightId eq '{flight_id}' and scheduled eq '{day}'"
    iso_probe = get("/query", {"filter": iso_search, "count": str(QUERY_COUNT)}) or {}

    save("health.json", get("/heartBeat"))

    return {
        "search_flight_id": flight_id,
        "iso_date_probe_flights": len(iso_probe.get("flights") or []),
        "live_calls": calls,
    }


def main() -> None:
    key = os.environ.get("SWEDAVIA_API_KEY", "").strip()
    if not key:
        sys.exit(
            "SWEDAVIA_API_KEY is not set. Run: "
            "uv run --env-file .env python -m scripts.record_fixtures"
        )
    today = datetime.now(STOCKHOLM).date()
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        summary = record(client, FIXTURES, today, time.sleep, key)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
