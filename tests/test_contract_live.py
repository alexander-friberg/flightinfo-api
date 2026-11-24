"""Contract test against the real API: does Swedavia still answer in the shape we parse?

Excluded from normal runs (it costs quota). Run it on purpose:

    uv run --env-file .env pytest -m live
"""

import os
from datetime import datetime

import httpx
import pytest

from flightboard.domain.airports import STOCKHOLM
from scripts.record_fixtures import BASE_URL


@pytest.mark.live
def test_arrivals_response_has_the_documented_top_level_shape() -> None:
    key = os.environ.get("SWEDAVIA_API_KEY", "").strip()
    if not key:
        pytest.skip("SWEDAVIA_API_KEY is not set; run with uv run --env-file .env")
    day = datetime.now(STOCKHOLM).date().isoformat()

    response = httpx.get(
        f"{BASE_URL}/ARN/arrivals/{day}",
        headers={"Ocp-Apim-Subscription-Key": key, "Accept": "application/json"},
        timeout=15.0,
    )

    if response.status_code == 204:
        return
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"to", "numberOfFlights", "flights"}
    assert body["to"]["arrivalAirportIata"] == "ARN"
    assert isinstance(body["flights"], list)
    assert body["numberOfFlights"] == len(body["flights"])
