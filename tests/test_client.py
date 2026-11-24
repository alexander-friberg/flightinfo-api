"""SwedaviaClient against a fake Swedavia (httpx.MockTransport): no network, no real key."""

import json
from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

import httpx
import pytest

from flightboard.api.client import QUERY_COUNT, SwedaviaClient
from flightboard.api.errors import (
    ApiError,
    ApiUnavailableError,
    AuthError,
    BadQueryError,
    QuotaExceededError,
)
from flightboard.api.protocols import FlightSource
from flightboard.config import Settings
from flightboard.domain.models import Direction

FIXTURES = Path(__file__).parent / "fixtures"
KEY = "fake-key"  # low entropy on purpose: secret scanners ignore it
SETTINGS = Settings(api_key=KEY, timeout_s=3.0)
DAY = date(2026, 11, 24)

Handler = Callable[[httpx.Request], httpx.Response]


def fixture(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class Recorder:
    """Records every request and answers with a fixed response."""

    def __init__(self, response: httpx.Response | Handler) -> None:
        self.requests: list[httpx.Request] = []
        self.response = response

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if isinstance(self.response, httpx.Response):
            return self.response
        return self.response(request)


def ticks(*values: float) -> Callable[[], float]:
    it: Iterator[float] = iter(values)
    return lambda: next(it)


def client_for(
    handler: Handler, clock: Callable[[], float] = lambda: 0.0
) -> tuple[SwedaviaClient, httpx.Client]:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return SwedaviaClient(SETTINGS, http, clock=clock), http


def json_response(name: str) -> httpx.Response:
    return httpx.Response(200, json=fixture(name))


# --- protocol -----------------------------------------------------------------------------


def test_client_satisfies_the_flight_source_protocol() -> None:
    """Checked by mypy: the assignment fails type-checking if a method is missing or wrong."""
    client, _ = client_for(Recorder(httpx.Response(200, json={})))

    source: FlightSource = client

    assert source is client


# --- requests -----------------------------------------------------------------------------


def test_arrivals_request_url_headers_and_timeout() -> None:
    api = Recorder(json_response("arrivals_ARN.json"))
    client, _ = client_for(api)

    client.arrivals("ARN", DAY)

    [request] = api.requests
    assert request.method == "GET"
    assert str(request.url) == "https://api.swedavia.se/flightinfo/v2/ARN/arrivals/2026-11-24"
    assert request.headers["Ocp-Apim-Subscription-Key"] == KEY
    assert request.headers["Accept"] == "application/json"
    assert request.extensions["timeout"]["read"] == 3.0


def test_departures_request_url() -> None:
    api = Recorder(json_response("departures_ARN.json"))
    client, _ = client_for(api)

    client.departures("GOT", date(2026, 1, 5))

    assert str(api.requests[0].url).endswith("/GOT/departures/2026-01-05")


def test_query_sends_encoded_filter_and_count_without_continuation_token() -> None:
    api = Recorder(json_response("query_sample.json"))
    client, _ = client_for(api)

    client.query("flightId eq 'AY808' and scheduled eq '261124'")

    [request] = api.requests
    assert request.url.path == "/flightinfo/v2/query"
    assert request.url.params["filter"] == "flightId eq 'AY808' and scheduled eq '261124'"
    assert request.url.params["count"] == str(QUERY_COUNT) == "1000"
    assert "continuationtoken" not in request.url.params
    assert " " not in str(request.url) and "'" not in str(request.url)
    assert request.headers["Ocp-Apim-Subscription-Key"] == KEY


def test_heartbeat_request() -> None:
    api = Recorder(httpx.Response(200, json="IsAlive"))
    client, _ = client_for(api)

    client.health()

    assert str(api.requests[0].url) == "https://api.swedavia.se/flightinfo/v2/heartBeat"
    assert api.requests[0].headers["Ocp-Apim-Subscription-Key"] == KEY


def test_key_never_appears_in_any_url() -> None:
    api = Recorder(httpx.Response(200, json={}))
    client, _ = client_for(api)

    client.arrivals("ARN", DAY)
    client.departures("ARN", DAY)
    client.query("flightId eq 'SK1'")
    client.health()

    assert all(KEY not in str(r.url) for r in api.requests)


# --- successful responses -----------------------------------------------------------------


def test_arrivals_and_departures_are_parsed_from_the_fixtures() -> None:
    arrivals, _ = client_for(Recorder(json_response("arrivals_ARN.json")))
    departures, _ = client_for(Recorder(json_response("departures_ARN.json")))

    assert len(arrivals.arrivals("ARN", DAY)) == 289
    flights = departures.departures("ARN", DAY)
    assert len(flights) == 277
    assert {f.direction for f in flights} == {Direction.DEPARTURE}


def test_query_is_parsed_from_the_fixture() -> None:
    client, _ = client_for(Recorder(json_response("query_sample.json")))

    [flight] = client.query("flightId eq 'AY808'")

    assert flight.flight_id == "AY808"


@pytest.mark.parametrize("method", ["arrivals", "departures"])
def test_no_content_means_no_flights(method: str) -> None:
    client, _ = client_for(Recorder(httpx.Response(204)))

    assert getattr(client, method)("ARN", DAY) == []


def test_empty_query_result_means_no_flights() -> None:
    client, _ = client_for(Recorder(httpx.Response(204)))

    assert client.query("flightId eq 'NOPE'") == []


def test_body_that_is_not_json_is_an_api_error() -> None:
    client, _ = client_for(Recorder(httpx.Response(200, text="<html>oops</html>")))

    with pytest.raises(ApiError, match="valid JSON"):
        client.arrivals("ARN", DAY)


# --- errors -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, AuthError),
        (403, AuthError),
        (429, QuotaExceededError),
        (500, ApiUnavailableError),
        (502, ApiUnavailableError),
        (503, ApiUnavailableError),
        (400, ApiError),
        (404, ApiError),
        (304, ApiError),
    ],
)
def test_status_codes_map_to_error_types(status: int, error: type[ApiError]) -> None:
    client, _ = client_for(Recorder(httpx.Response(status)))

    with pytest.raises(error) as raised:
        client.arrivals("ARN", DAY)

    assert str(status) in str(raised.value)


def test_400_on_a_query_is_a_bad_query() -> None:
    client, _ = client_for(Recorder(httpx.Response(400, json={"message": "Invalid filter"})))

    with pytest.raises(BadQueryError, match="Invalid filter"):
        client.query("airport eq")


def test_400_on_a_list_is_not_reported_as_a_bad_query() -> None:
    client, _ = client_for(Recorder(httpx.Response(400)))

    with pytest.raises(ApiError) as raised:
        client.departures("ARN", DAY)

    assert not isinstance(raised.value, BadQueryError)


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"message": "Rate limit is exceeded. Try again in 1 seconds."}, "too fast"),
        (
            {"message": "Out of call volume quota. Quota will be replenished in 5.00:00:00."},
            "quota is used up",
        ),
    ],
)
def test_quota_errors_explain_which_limit_when_the_response_says(
    body: object, expected: str
) -> None:
    client, _ = client_for(Recorder(httpx.Response(429, json=body)))

    with pytest.raises(QuotaExceededError) as raised:
        client.query("flightId eq 'SK1'")

    message = str(raised.value).lower()
    assert expected in message
    assert str(body["message"]).lower() in message  # type: ignore[index]


def test_quota_error_names_both_limits_when_the_response_does_not_say() -> None:
    client, _ = client_for(Recorder(httpx.Response(429)))

    with pytest.raises(QuotaExceededError) as raised:
        client.query("flightId eq 'SK1'")

    message = str(raised.value).lower()
    assert "rate limit" in message
    assert "monthly quota" in message


def test_auth_error_tells_the_user_what_to_check() -> None:
    client, _ = client_for(Recorder(httpx.Response(401)))

    with pytest.raises(AuthError, match="SWEDAVIA_API_KEY"):
        client.arrivals("ARN", DAY)


@pytest.mark.parametrize(
    "exception",
    [
        httpx.ConnectTimeout("timed out"),
        httpx.ReadTimeout("timed out"),
        httpx.ConnectError("no route"),
        httpx.RemoteProtocolError("bad"),
    ],
)
def test_network_failures_are_api_unavailable(exception: httpx.HTTPError) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise exception

    client, _ = client_for(fail)

    with pytest.raises(ApiUnavailableError):
        client.departures("ARN", DAY)


def echo_key_with(status: int) -> Handler:
    """A server that puts the received key into its error message."""

    def handler(request: httpx.Request) -> httpx.Response:
        echoed = request.headers["Ocp-Apim-Subscription-Key"]
        return httpx.Response(status, json={"message": f"Quota exceeded for key {echoed}"})

    return handler


def test_errors_never_contain_the_key_or_headers() -> None:
    handlers: list[Handler] = [
        echo_key_with(429),
        echo_key_with(400),
        Recorder(httpx.Response(401)),
        Recorder(httpx.Response(500)),
    ]
    for handler in handlers:
        client, _ = client_for(handler)
        with pytest.raises(ApiError) as raised:
            client.query("flightId eq 'SK1'")
        text = f"{raised.value} {raised.value!r}"
        assert KEY not in text
        assert "Ocp-Apim-Subscription-Key" not in text
        assert raised.value.__cause__ is None
        assert raised.value.__suppress_context__


# --- health ------------------------------------------------------------------------------


def test_health_is_judged_by_status_and_measures_latency() -> None:
    client, _ = client_for(Recorder(httpx.Response(200, json="IsAlive")), ticks(10.0, 10.042))

    status = client.health()

    assert status.ok is True
    assert status.status_code == 200
    assert status.latency_ms == pytest.approx(42.0)


@pytest.mark.parametrize("body", ["IsAlive", {}, None, "anything"])
def test_health_ignores_the_body(body: object) -> None:
    client, _ = client_for(Recorder(httpx.Response(200, json=body)))

    assert client.health().ok is True


def test_unhealthy_status_is_reported_not_raised() -> None:
    client, _ = client_for(Recorder(httpx.Response(503)), ticks(0.0, 0.5))

    status = client.health()

    assert status.ok is False
    assert status.status_code == 503
    assert status.latency_ms == pytest.approx(500.0)
    assert status.message is not None and "503" in status.message


def test_health_timeout_is_reported_without_a_status_code() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    client, _ = client_for(fail, ticks(0.0, 3.0))

    status = client.health()

    assert status.ok is False
    assert status.status_code is None
    assert status.latency_ms == pytest.approx(3000.0)
    assert status.message is not None and KEY not in status.message


def test_client_does_not_close_the_injected_http_client() -> None:
    client, http = client_for(Recorder(httpx.Response(200, json={})))

    client.arrivals("ARN", DAY)

    assert not http.is_closed


def test_redirects_are_never_followed_so_the_key_stays_with_swedavia() -> None:
    api = Recorder(httpx.Response(302, headers={"Location": "https://elsewhere.example/steal"}))
    http = httpx.Client(transport=httpx.MockTransport(api), follow_redirects=True)
    client = SwedaviaClient(SETTINGS, http)

    with pytest.raises(ApiError, match="302"):
        client.arrivals("ARN", DAY)

    assert [r.url.host for r in api.requests] == ["api.swedavia.se"]
