# Swedavia Flight Board

[![CI](https://github.com/alexander-friberg/flightinfo-api/actions/workflows/ci.yml/badge.svg)](https://github.com/alexander-friberg/flightinfo-api/actions/workflows/ci.yml)

A Python terminal app that shows real-time arrivals and departures for Sweden's ten Swedavia
airports, using the [Swedavia FlightInfo API v2](https://apideveloper.swedavia.se).

It recreates an existing application that is known only from a video and a few code fragments,
rebuilt with a layered structure, dependency injection and a test suite that never needs the
network. The research behind it is in [`docs/research.md`](docs/research.md), and the full
project documentation is in [`docs/documentation.md`](docs/documentation.md).

## Features
The menu has the original application's six options:

1. **Arrivals** for an airport and date
2. **Departures** for an airport and date
3. **Search** for a flight number on a date, across all Swedavia airports
4. **OData query**: ready-made queries (departures, arrivals, one flight, cancelled flights) or
   your own filter
5. **HeartBeat**: a `ping`-style health check of the API
6. **Full-auto demo**: every endpoint once, with no input

After options 1 and 2 you can also show a **destination overview**: every city with its country
and number of flights, optionally filtered by country or city.

Airports can be given as an IATA code or a city name (`arn`, `Visby`, `göteborg`). Dates accept
`YYYY-MM-DD`, `today`, `tomorrow`, `yesterday`, `now`, or Enter for today. Times are shown in UTC and
Swedish local time.

## Requirements
- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- For live data: a subscription key for the FlightInfo product from the
  [Swedavia developer portal](https://apideveloper.swedavia.se)

## Install
```
git clone https://github.com/alexander-friberg/flightinfo-api.git
cd flightinfo-api
uv sync
```

## Configure
Copy the example file and put your subscription key in it:
```
cp .env.example .env
```
```
SWEDAVIA_API_KEY=<your key>
```
`.env` is git-ignored, so the key never ends up in the repository. Optional settings:

| Variable | Default | Meaning |
|---|---|---|
| `SWEDAVIA_TIMEOUT_S` | `10` | Seconds to wait for the API |
| `SWEDAVIA_CACHE_TTL_S` | `120` | Seconds to reuse a recent answer (0 turns the cache off) |

## Run
With live data:
```
uv run --env-file .env python -m flightboard
```

Without a key or network, on one recorded day at Stockholm Arlanda:
```
uv run python -m flightboard --offline
```

The free API tier has a small monthly quota. Offline mode costs nothing, and recent answers are
cached for two minutes to avoid repeat calls.

## Tests
Run the test suite (no network, no key needed):
```
uv run pytest
```

Run every check that CI runs (lint, formatting, strict type checking, tests):
```
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
```

A separate contract test checks that the live API still answers in the expected shape. It's
excluded by default because it uses the API quota:
```
uv run --env-file .env pytest -m live
```

## Project structure
```
src/flightboard/
├── __main__.py   # composition root: builds the real objects, --offline
├── config.py     # settings from the environment; the key is masked
├── domain/       # flight model and airports (no I/O)
├── api/          # HTTP client, parser, errors, cache, offline source
├── services/     # flights, search, OData, heartbeat, destination overview
├── data/         # city → country lookup and offline sample data
└── cli/          # menu, prompts, flight card, paging, demo
tests/            # unit tests, fakes and recorded API responses
scripts/          # one-off tools: record fixtures, build city_country.json
docs/             # research, API reference, documentation, task log
```

Each layer only depends on the layers inside it (`cli` → `services` → `domain`, with `api`
supplying the data), and every external dependency is passed in. That's what lets the whole
application be tested without the live API.
