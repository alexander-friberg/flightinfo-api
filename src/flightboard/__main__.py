"""The composition root: the only place that builds real objects and wires them together.

uv run --env-file .env python -m flightboard      # live API (needs SWEDAVIA_API_KEY)
uv run python -m flightboard --offline            # recorded sample data, no key, no network
"""

import argparse
import os
import sys
import time
from collections.abc import Callable, Sequence
from datetime import datetime

import httpx

from flightboard.api.caching import CachingFlightSource
from flightboard.api.client import SwedaviaClient
from flightboard.api.offline import OfflineFlightSource
from flightboard.api.protocols import FlightSource
from flightboard.cli.app import TITLE, App
from flightboard.cli.io import Console
from flightboard.cli.menu import run_menu
from flightboard.config import ConfigError, load_settings
from flightboard.data.lookup import load_lookup
from flightboard.domain.airports import STOCKHOLM


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="flightboard",
        description="Arrivals and departures at Sweden's Swedavia airports (FlightInfo API v2).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="use recorded sample data: no API key, no network, no quota",
    )
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    transport: httpx.BaseTransport | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Run the app; returns the process exit code (2 for a configuration error).

    `transport` and `sleep` exist for tests: a fake Swedavia and no real waiting.
    """
    args = parse_args(argv)
    console = Console(read=input, write=print)

    def app_for(source: FlightSource, title: str, pings: int) -> App:
        return App(
            console=console,
            source=source,
            lookup=load_lookup(),
            today=lambda: datetime.now(STOCKHOLM).date(),
            sleep=sleep,
            title=title,
            ping_count=pings,
        )

    try:
        if args.offline:
            offline = OfflineFlightSource()
            run_menu(app_for(offline, f"Swedavia FlightInfo API v2 – {offline.label}", pings=1))
            return 0

        try:
            settings = load_settings(os.environ)
        except ConfigError as error:
            print(error, file=sys.stderr)
            return 2
        with httpx.Client(transport=transport) as http:
            source = CachingFlightSource(SwedaviaClient(settings, http), settings.cache_ttl_s)
            run_menu(app_for(source, TITLE, pings=5))
        return 0
    except (KeyboardInterrupt, EOFError):
        # Ctrl-C or end of input at a prompt: leave like the menu's own "q", not with a traceback.
        print("\nGoodbye.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
