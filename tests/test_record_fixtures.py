"""The fixture recorder, run against a fake Swedavia: no network, no key, no real waiting."""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from scripts.record_fixtures import (
    BASE_URL,
    CONTINUATION_PLACEHOLDER,
    KeyLeakError,
    record,
)

KEY = "test-key-0123456789abcdef"  # gitleaks:allow (made-up key for tests)
TODAY = date(2026, 11, 24)

SK532 = {"flightId": "SK532", "departureTime": {"scheduledUtc": "2026-11-24T16:25:00Z"}}
DEPARTURES = {
    "from": {"departureAirportIata": "ARN"},
    "numberOfFlights": 2,
    "flights": [{"flightId": "", "departureTime": {}}, SK532],
}


class FakeSwedavia:
    def __init__(self, leak_key_in: str | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self.leak_key_in = leak_key_in

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        body: object
        if path.endswith("/arrivals/2026-11-24"):
            body = {"to": {"arrivalAirportIata": "ARN"}, "numberOfFlights": 0, "flights": []}
        elif path.endswith("/departures/2026-11-24"):
            body = DEPARTURES
        elif path.endswith("/query"):
            body = {"flights": [{"departure": SK532}], "continuationtoken": "H4sIAAAAAAAEAEtMTgYA"}
        elif path.endswith("/heartBeat"):
            body = "IsAlive"  # the real body; the docs claim {}
        else:
            return httpx.Response(404)
        if self.leak_key_in and path.endswith(self.leak_key_in):
            body = {"echo": KEY}
        return httpx.Response(200, json=body)


def run(tmp_path: Path, api: FakeSwedavia) -> tuple[list[float], dict[str, object]]:
    sleeps: list[float] = []
    with httpx.Client(transport=httpx.MockTransport(api), base_url=BASE_URL) as client:
        summary = record(client, tmp_path, TODAY, sleeps.append, KEY)
    return sleeps, summary


def test_makes_five_calls_in_order_with_the_key_only_in_the_header(tmp_path: Path) -> None:
    api = FakeSwedavia()

    run(tmp_path, api)

    assert [r.url.path for r in api.requests] == [
        "/flightinfo/v2/ARN/arrivals/2026-11-24",
        "/flightinfo/v2/ARN/departures/2026-11-24",
        "/flightinfo/v2/query",
        "/flightinfo/v2/query",
        "/flightinfo/v2/heartBeat",
    ]
    for request in api.requests:
        assert request.headers["Ocp-Apim-Subscription-Key"] == KEY
        assert request.headers["Accept"] == "application/json"
        assert KEY not in str(request.url)


def test_search_query_uses_a_real_flight_id_without_airport(tmp_path: Path) -> None:
    api = FakeSwedavia()

    run(tmp_path, api)

    search, probe = api.requests[2], api.requests[3]
    assert search.url.params["filter"] == "flightId eq 'SK532' and scheduled eq '261124'"
    assert search.url.params["count"] == "1000"
    assert probe.url.params["filter"] == "flightId eq 'SK532' and scheduled eq '2026-11-24'"
    assert "airport" not in search.url.params["filter"]


def test_waits_at_least_two_seconds_between_calls(tmp_path: Path) -> None:
    sleeps, _ = run(tmp_path, FakeSwedavia())

    assert len(sleeps) == 4
    assert all(s >= 2.0 for s in sleeps)


def test_saves_four_pretty_printed_fixtures(tmp_path: Path) -> None:
    run(tmp_path, FakeSwedavia())

    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["arrivals_ARN.json", "departures_ARN.json", "health.json", "query_sample.json"]
    text = (tmp_path / "departures_ARN.json").read_text(encoding="utf-8")
    assert json.loads(text) == DEPARTURES
    assert text.startswith("{\n  ")
    assert json.loads((tmp_path / "health.json").read_text(encoding="utf-8")) == "IsAlive"


def test_continuation_token_is_replaced_so_secret_scanners_stay_quiet(tmp_path: Path) -> None:
    run(tmp_path, FakeSwedavia())

    saved = json.loads((tmp_path / "query_sample.json").read_text(encoding="utf-8"))
    assert saved["continuationtoken"] == CONTINUATION_PLACEHOLDER
    assert saved["flights"] == [{"departure": SK532}]


def test_summary_reports_the_iso_date_probe(tmp_path: Path) -> None:
    _, summary = run(tmp_path, FakeSwedavia())

    assert summary["search_flight_id"] == "SK532"
    assert summary["iso_date_probe_flights"] == 1
    assert summary["live_calls"] == 5


@pytest.mark.parametrize("endpoint", ["arrivals/2026-11-24", "query", "heartBeat"])
def test_fails_if_the_key_ends_up_in_a_saved_file(tmp_path: Path, endpoint: str) -> None:
    with pytest.raises(KeyLeakError) as error:
        run(tmp_path, FakeSwedavia(leak_key_in=endpoint))

    assert KEY not in str(error.value)


def test_http_errors_stop_the_recording(tmp_path: Path) -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Access denied"})

    with (
        httpx.Client(transport=httpx.MockTransport(broken), base_url=BASE_URL) as client,
        pytest.raises(httpx.HTTPStatusError),
    ):
        record(client, tmp_path, TODAY, lambda _: None, KEY)


def test_a_day_without_departures_stops_with_a_clear_message(tmp_path: Path) -> None:
    def no_content(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    with (
        httpx.Client(transport=httpx.MockTransport(no_content), base_url=BASE_URL) as client,
        pytest.raises(RuntimeError, match="No departures"),
    ):
        record(client, tmp_path, TODAY, lambda _: None, KEY)
