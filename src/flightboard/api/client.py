"""The only code that talks to Swedavia. It turns HTTP into `Flight` objects or `ApiError`s."""

import time
from collections.abc import Callable
from datetime import date

import httpx

from flightboard.api.errors import (
    ApiError,
    ApiUnavailableError,
    AuthError,
    BadQueryError,
    QuotaExceededError,
)
from flightboard.api.parsing import parse_flights, parse_query
from flightboard.config import Settings
from flightboard.domain.models import Direction, Flight, HealthStatus

# The query endpoint returns 25 flights unless told otherwise; 1000 is its maximum.
QUERY_COUNT = 1000


class SwedaviaClient:
    """`FlightSource` backed by the FlightInfo v2 API.

    The `httpx.Client` is injected (tests pass one with a `MockTransport`) and is closed by
    whoever created it, not by this class.
    """

    def __init__(
        self,
        settings: Settings,
        http: httpx.Client,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._settings = settings
        self._http = http
        self._clock = clock

    def arrivals(self, airport: str, day: date) -> list[Flight]:
        return parse_flights(self._get(f"/{airport}/arrivals/{day:%Y-%m-%d}"), Direction.ARRIVAL)

    def departures(self, airport: str, day: date) -> list[Flight]:
        return parse_flights(
            self._get(f"/{airport}/departures/{day:%Y-%m-%d}"), Direction.DEPARTURE
        )

    def query(self, odata_filter: str) -> list[Flight]:
        params = {"filter": odata_filter, "count": str(QUERY_COUNT)}
        return parse_query(self._get("/query", params, is_query=True))

    def health(self) -> HealthStatus:
        start = self._clock()
        try:
            response = self._send("/heartBeat")
        except ApiError as error:
            return HealthStatus(False, None, self._ms_since(start), str(error))
        latency = self._ms_since(start)
        # Judged by status only: the docs promise `{}`, the real body is "IsAlive".
        if response.is_success:
            return HealthStatus(True, response.status_code, latency)
        message = f"Heartbeat answered HTTP {response.status_code}."
        return HealthStatus(False, response.status_code, latency, message)

    def _get(
        self, path: str, params: dict[str, str] | None = None, is_query: bool = False
    ) -> object:
        response = self._send(path, params)
        if response.status_code == 204:
            return None
        if not response.is_success:
            raise self._error(response, is_query) from None
        try:
            return response.json()
        except ValueError:
            raise ApiError("Swedavia sent a response that isn't valid JSON.") from None

    def _send(self, path: str, params: dict[str, str] | None = None) -> httpx.Response:
        try:
            return self._http.get(
                self._settings.base_url + path,
                params=params,
                headers={
                    "Ocp-Apim-Subscription-Key": self._settings.api_key,
                    "Accept": "application/json",
                },
                timeout=self._settings.timeout_s,
                # httpx keeps custom headers on a redirect to another host, so never follow
                # one: the key must only ever reach Swedavia.
                follow_redirects=False,
            )
        except httpx.TimeoutException:
            raise ApiUnavailableError(
                f"Swedavia didn't answer within {self._settings.timeout_s:g} s. Try again later."
            ) from None
        except httpx.HTTPError as error:
            raise ApiUnavailableError(
                f"Couldn't reach Swedavia ({type(error).__name__}). Check your connection."
            ) from None

    def _error(self, response: httpx.Response, is_query: bool) -> ApiError:
        status = response.status_code
        detail = self._scrub(_server_message(response))
        if status in (401, 403):
            return AuthError(
                f"Swedavia rejected the API key (HTTP {status}). Check SWEDAVIA_API_KEY in .env "
                "and that your subscription includes FlightInfo."
            )
        if status == 429:
            return QuotaExceededError(_quota_message(detail))
        if status >= 500:
            return ApiUnavailableError(
                f"Swedavia had a server error (HTTP {status}). Try again later."
            )
        if status == 400 and is_query:
            return BadQueryError(
                f"Swedavia rejected the filter (HTTP 400): {detail or 'no detail'}"
            )
        return ApiError(f"Unexpected answer from Swedavia (HTTP {status}).")

    def _scrub(self, text: str) -> str:
        key = self._settings.api_key
        return text.replace(key, "***") if key else text

    def _ms_since(self, start: float) -> float:
        return (self._clock() - start) * 1000


def _server_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""
    message = body.get("message") if isinstance(body, dict) else None
    return message.strip() if isinstance(message, str) else ""


def _quota_message(detail: str) -> str:
    lowered = detail.lower()
    if "rate limit" in lowered:
        return (
            f"Too many requests too fast (HTTP 429): the query endpoint allows one call per 2 s. "
            f"{detail}"
        ).strip()
    if "quota" in lowered:
        return f"The monthly API quota is used up (HTTP 429). {detail}".strip()
    return (
        "Swedavia said 'too many requests' (HTTP 429): either the one-call-per-2-s rate limit "
        "or the monthly quota. Wait a moment and try again."
    )
