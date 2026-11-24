# Research

## Overview
The original application gathers data from the **Swedavia FlightInfo API v2** and displays real-time flight data for Sweden's ten Swedavia airports in the terminal.

The goal of this project is to **recreate** that application from the information available (a video walkthrough and a few known source code fragments), and in doing so improve its structure: a decoupled, modular codebase built around dependency injection so that every part can be tested without touching the live API.

---

## The Swedavia API

**API reference: received in full.** Alex copied the official operation pages for all four
FlightInfo v2 endpoints from the developer portal on 2026-11-24. The cleaned copy is in
[`api-reference.md`](api-reference.md), and it is the source for everything in this section.
What's still open is how the live API behaves compared with the docs (which fields are actually
filled in, and the inconsistencies listed below). Task 05 checks that against real responses.

### Access & authentication
- Developer portal: https://apideveloper.swedavia.se (register, subscribe to the FlightInfo product, get a subscription key)
- Authentication is a subscription key sent in the header `Ocp-Apim-Subscription-Key: <key>` (Azure API Management). It can also be passed as a `?subscription-key=` query parameter, but the header is preferred so the key never ends up in logged URLs.
- Response format is requested with `Accept: application/json`.

### Quota
The free tier is rate limited per month. The public FAQ states 10 000 requests/month for FlightInfo, while the dev portal FAQ states 1 000. **Assume the lower number until verified on my own subscription page.** (**Alex:** still unchecked after task 05; 6 calls were safe under either figure.)

Consequences for the design:
- Tests must **never** call the live API (see Testing strategy in `documentation.md`).
- The heartbeat must not poll aggressively (see Questions).
- Caching responses for a short time is worth considering.

### Endpoints (FlightInfo v2)
| Purpose | Endpoint (relative to `https://api.swedavia.se/flightinfo/v2`) | Documented responses | Used by menu option |
|---|---|---|---|
| Arrivals for one airport and day | `GET /{iata}/arrivals/{yyyy-mm-dd}` | 200, 204, 304, 400, 500 | 1. View arrivals (+ destination overview) |
| Departures for one airport and day | `GET /{iata}/departures/{yyyy-mm-dd}` | 200, 204, 304, 400, 500 | 2. View departures (+ destination overview) |
| Free-form OData query | `GET /query?filter=<odata>&count=<n>` | 200, 429 | 3. Search flight, 4. Run OData queries |
| Health | `GET /heartBeat` (docs say `{}`; really returns `"IsAlive"`) | 200 | 5. Check API health |

Behaviour worth designing for:
- **204 No Content** is a normal answer from arrivals/departures (no flights). It means an empty list, not an error.
- **Every response field is optional.** Parsing must never assume a field exists.
- **Query rate limit: one call per two seconds.** Faster calls get `429 Too Many Requests`. This is separate from the monthly quota, which also answers with 429.
- **Query `count`** defaults to **25** (max 1000). Without it, a busy airport's day is silently cut short.
- **`continuationtoken`** returns flights *updated since* the call that produced it. It is a change feed, not a page cursor.
- `diIndicator` can be `D`, `I` **or `S` (Schengen)**.
- Arrivals carry `baggage` (belt, first/last bag). Departures carry `checkIn` (status, desks) and gate open/close times.

OData filter fields: `airport`, `flightType` (`A`/`D`), `scheduled` (local Swedish date, `YYMMDD`), `estimated` (UTC datetime), `flightStatus`, `flightId`. Operators: `and or eq ne gt ge lt le`. Examples:
- `airport eq 'ARN' and flightType eq 'D'`
- `airport eq 'ARN' and scheduled eq '190921' and flightType eq 'D' and flightId eq 'SK007'` (single flight)

### Inconsistencies in the official docs (verified 2026-11-24, task 05)
Checked against real responses recorded in `tests/fixtures/` (ARN, 2026-11-24, 6 live calls):

| Question | Result |
|---|---|
| `type eq 'D' and airline eq 'SK'` in the airline example: are `type`/`airline` really filter fields? | **Not verified** (no call budget left). Use only the documented fields. |
| Is `airlineOperator.icao` the ICAO code, as the name says, or the IATA code, as the description says? | **ICAO.** It's `SAS` where `iata` is `SK`. Norwegian appears twice: `DY`/`NOZ` and `D8`/`NSZ`. The description is wrong. |
| Arrivals: "zero or more" flights; departures: "one or more"? | **Not observable** (ARN had 289/277 flights). Still treat both lists as possibly empty, and 204 as empty. |
| `scheduled`: `YYMMDD` only, or `YYYY-MM-DD` too? | **Both work.** `scheduled eq '261124'` and `scheduled eq '2026-11-24'` each found the same flight. |
| Is `{date}` in arrivals/departures a local Swedish day or a UTC day? | **Local.** ARN arrivals for 2026-11-24 ran from `2026-11-23T23:00Z` to `2026-11-24T22:55Z`, which is 00:00–23:55 Swedish time (CET). |
| Does a query **without** `airport` work? | **Yes.** `flightId eq 'AY808' and scheduled eq '261124'` returned the ARN→HEL departure. Search needs no airport. |
| Does `/heartBeat` count against the monthly quota? | **Not observable** from the response. Assume yes and keep the heartbeat short. |
| What does `/heartBeat` return? | **The docs are wrong:** the body is the JSON string `"IsAlive"`, not `{}`. Health checks should rely on the status code, not the body. |
| Query items: `arrival` or `departure` plus `scheduledDate`? | Each item has **only** `arrival` or `departure`; `scheduledDate` was absent. Don't rely on it. |
| `numberOfFlights` | Equals `len(flights)` in both lists. |

Other findings from the fixtures:
- **Missing fields are omitted, not empty.** A flight without a gate has no `gate` key at all (it isn't `""`). The parser must use `.get()` everywhere.
- **No ghost entries** in today's ARN data. `tests/fixtures/ghost_entries.json` is hand-made from the rules in `_is_valid_flight()` so task 06 can still test them.
- **Status codes seen**, as `flightLegStatus` → `flightLegStatusEnglish` across 566 flights. The English text is always present, and some of it includes a time:

  | Code | English text | Count |
  |---|---|---|
  | `SCH` | Scheduled | 218 |
  | `DEL` | **Deleted** (not "delayed") | 117 |
  | `LAN` | Landed HH:MM | 94 |
  | `ACT` | Departed | 94 |
  | `SEQ` | Estimated HH:MM | 41 |
  | `CAN` | Cancelled | 2 |
- **Should "Deleted" flights be shown at all?** About one in five flights is `DEL`, and the original's card in the video only shows a `Scheduled` flight. It's not clear whether "Deleted" means removed from the schedule or a codeshare duplicate. **Decision (Alex, 2026-11-24): list them as-is**, with their status text shown unchanged. They're real records, and the original has no known filter.
- **`diIndicator`:** `S` (Schengen) is the most common value (165 of 289 arrivals), then `D`, then `I`.
- The header's own airport name is `"Stockholm ARN"`, not "Stockholm Arlanda". Use `AIRPORTS` for display names.

### Airports
In the order and with the names the original lists them (see "What we know (from the video)").

| IATA | Airport |
|---|---|
| ARN | Stockholm Arlanda |
| GOT | Göteborg Landvetter |
| BMA | Stockholm Bromma |
| MMX | Malmö |
| LLA | Luleå |
| UME | Umeå |
| OSD | Östersund (Swedavia's official name is Åre Östersund) |
| VBY | Visby |
| RNB | Ronneby |
| KRN | Kiruna |

---

## Original application – core

Source: the project description shown in the video. It describes a Python terminal application where all four available API endpoints are implemented and covered.

### airport.py – Main file (entry point)
- API key in **plaintext** at the top of the file, a `BASE_URL` variable and a `HEADERS` dictionary.
- `AIRPORTS` dict with IATA codes as keys and airport names as values.
- An `_AIRPORT_ALIASES` dict (lowercase alias → IATA), so the user can type e.g. a city name instead of the code.
- Interactive main menu with six options plus quit (exact labels in "What we know (from the video)"):
  1. Arrivals for an airport & date
  2. Departures for an airport & date
  3. Search a specific flight number
  4. OData query (query endpoint)
  5. HeartBeat, API health check
  6. Demonstrate all endpoints automatically
  - q. Quit
- Uses all four available API endpoints.
- Shows a list of the ten airports when asking the user to pick one.

### destinationer.py – Helper script
Fetches arrivals or departures and lists every unique city together with its country (looked up in `city_country.json`) and how many flights went there. Results can be filtered by country or city name.

The video shows more of how it works:
- It has its own `main()`. It runs once and exits; there is no main loop.
- It prompts in this order:
  1. Airport via `_choose_airport()`, looping until valid. This is the same helper `airport.py` uses.
  2. Date via `_choose_date()`, looping until valid.
  3. `input("Filter? ")`.
  4. `input("Välj [1-3]: ")`, looping until 1, 2 or 3; bad input prints "⚠ Skriv 1, 2 eller 3.".
- It then fetches from the API, prints the results and ends.

### city_country.json – Local database
Built from Swedavia's official statistics Excel file and used as a local lookup table by `destinationer.py`.

Confirmed by the project description shown in the video:
- Maps **263 cities to 59 countries**.
- Works as an **offline database**: country lookups cost **no extra API calls**. This matters for the quota, because only the arrivals/departures fetch counts against it.

Implications for the recreation:
- The JSON is static data that ships with the app, so it is loaded once at startup through an injected `CityCountryLookup` (tests use a small in-memory dict instead).
- The API returns city names in English (`…AirportEnglish`), so the JSON keys must use the same spelling, or the lookup needs normalisation (case, whitespace, diacritics). Verify against a fixture.

### The statistics file we have: `data/raw/destinations-statistik-2025.xlsx`
Swedavia's "Trafikflöde / Traffic by flight stage" statistics for **2025**, with passenger numbers per reporting airport, country and city. Sheets:

| Sheet | Contents | Columns (after 6 header rows) |
|---|---|---|
| `fpl-land` | per airport → country → city, by quarter | airport, country, city, Q1–Q4, total |
| `land-fpl` | per country → city → airport, by quarter | country, city, airport, Q1–Q4, total |
| `tot per kvartal` | long format: airport, quarter, country, city, passengers | (header row says 2024, data says 2025) |
| `Avr utrpass Land fpl per kvarta` | departing **international** passengers, country → city | country, city, Q1–Q4, total |
| `avr utr pax per kvartal` | the same in long format | quarter, country, city, passengers |

Findings (counted with a quick stdlib script, before any build script exists):
- **It does not give 263 cities / 59 countries.** `land-fpl` has 345 cities in 67 countries, including Sweden (the build script's count, task 12). The international-only sheet has about 305 cities in 67 countries. The original was most likely built from an earlier year's file, so **263/59 can't be used as a test for our JSON**.
- Subtotal rows mix in with the data: `<COUNTRY> Summa` and `<City> Summa`. The build script must skip them.
- Placeholder values: `(tom)` (empty) as a city and as a country, and `UNKNOWN` as a country. Skip them.
- Countries are in English capitals (`AUSTRIA`, `GREAT BRITAIN`). Cities are mixed case (`Vienna`, `ALICANTE`, `ANNECY/MEYTHET`), and some are Swedish spellings (`Bagdad`, `Alger`), so they may not match the API's English `…AirportEnglish` names. Normalisation handles the case; the spelling has to be compared with real fixtures (task 05) and handled with a small alias table if needed.
- Some cities have no or zero passengers (e.g. `LINZ 0`). Keep them: the lookup is about which country a city is in, not traffic.
- **Decision:** build `city_country.json` from `land-fpl` (it includes domestic Swedish cities, which domestic flights need), with every country/city pair except subtotals and placeholders. The data test checks the counts the build script reports from this file, not the original's 263/59.

## Main loop
A simple `while True` loop waiting for user input with six options.

---

## Data model

### Flight (as displayed)
The original's flight card, as shown in the video (an arrival at ARN, labels as on screen):
```
[50] → SK532  |  SAS Scandinavian Airlines  (SK)
  From  : London LHR
  To    : (ARN)
  Status   : Scheduled
  Terminal : T5    Gate: N/A
  Baggage  : 3
  Sched : 16:25 UTC → 17:25 CET
  Est   : –
  Actual: –
  D/I     : I
  ────────────────────────────────────────
```
- Each card ends with a horizontal rule (under `D/I`, before the paging line). It was left out
  when the card was first transcribed, and added in task 13a.
- `[50]` is the running index in the list; `→` precedes the flight id.
- The airline and the other airport are shown as name + IATA code.
- The queried airport's name is blank: only `(ARN)` is shown.
- Times are shown as **UTC → local time** with the zone abbreviation (CET/CEST).
- Missing times are shown as `–` and a missing gate as `N/A`.
- D/I is the raw `diIndicator` (`D`, `I`, or `S` for Schengen).

### Display field → API field
From `api-reference.md`. The left column is the original's display; `X` is `arrival` or `departure`.

| Display | JSON key (arrivals) | JSON key (departures) | Notes |
|---|---|---|---|
| Flight id | `flightId` | `flightId` | e.g. `SK1415` |
| Airline | `airlineOperator.name` + `(airlineOperator.iata)` | same | |
| From | `departureAirportEnglish` + `flightLegIdentifier.departureAirportIata` | *(the airport queried)* | |
| To | *(the airport queried)* | `arrivalAirportEnglish` + `flightLegIdentifier.arrivalAirportIata` | Also the city used for the destination overview |
| Status | `locationAndStatus.flightLegStatusEnglish` | same | Code in `flightLegStatus` (e.g. `SCH`) |
| Terminal / Gate | `locationAndStatus.terminal`, `locationAndStatus.gate` | same | Shown on one line |
| Baggage | `baggage.baggageClaimUnit` | – | Arrivals only (belt) |
| Scheduled / Estimated / Actual | `arrivalTime.{scheduled,estimated,actual}Utc` | `departureTime.…Utc` | **UTC**; convert to `Europe/Stockholm` for display |
| D/I | `diIndicator` | `diIndicator` | `D`, `I` or `S` |

**Confirmed against the fixtures (task 05).** How often each display field was present in
today's ARN data:

| Field | Arrivals (289) | Departures (277) |
|---|---|---|
| flight id, airline name + IATA, other airport name + IATA, status, terminal, scheduled, D/I | always | always |
| gate | 129 | 151 |
| baggage belt | 226 | – |
| estimated | 130 | 12 |
| actual | 94 | 94 |

**City spelling vs `city_country.json` (matters for task 12).**
- The API writes cities in English, but cities with several airports get the airport code appended: `London LHR`, `Paris CDG`, `Istanbul SAW`, `New York EWR`. Strip a trailing three-letter upper-case code before looking a city up.
- The fixtures name 96 distinct cities. Stripping the code leaves 92 (`London LGW/LHR/STN`, `Istanbul IST/SAW` and `Paris CDG/ORY` each merge into one city). **80 of those 92** match a city in the 2025 Excel file, accent- and case-insensitively.
- The other 12 are the literal `"Unknown"` plus 11 spelling differences that need a small alias table:

  | API | Excel |
  |---|---|
  | Addis Abeba | Addis Ababa |
  | Geneva | Geneve |
  | Vaasa | Vasa |
  | Sal | Sal Island |
  | Sundsvall | Sundsvall Härnösand |
  | Hemavan Tärnaby | Hemavan |
  | Åre Östersund | Östersund |
  | Bergamo | Milan |
  | Malta | Valetta (the file's spelling) |
  | Munich | München |
  | Charleroi | Brussels (like Bergamo → Milan: a secondary airport filed under its city) |

  *(Task 12: Munich and Malta were first listed here as "no match". A search for "munch" missed
  `München` because of the ü. With these aliases, every city in the fixtures resolves except
  the literal "Unknown".)*

  `"Unknown"` should map straight to the "Unknown" country fallback, not count as an unmatched city.

---

## What we know (from the video)

### Main menu
```
Swedavia FlightInfo API v2  –  Python-klient
1. Ankomster (arrivals)  för en flygplats & datum
2. Avgångar (departures) för en flygplats & datum
3. Sök specifikt flightnummer
4. OData-förfrågan (query endpoint)
5. HeartBeat – hälsokontroll av API
6. Demonstrera alla endpoints automatiskt
q. Avsluta
```
In English: arrivals for an airport & date; departures for an airport & date; search a specific
flight number; OData query; HeartBeat API health check; demonstrate all endpoints automatically;
quit. There is no destinations option. Options 1 and 2 ask for both an airport and a date.

### Choosing an airport and a date
The airport prompt first lists the ten airports as `IATA – name`, in this order: ARN, GOT, BMA,
MMX, LLA, UME, OSD, VBY, RNB, KRN (see "Airports"). Then:
```
Ange IATA-kod eller stadsnamn (t.ex. ARN eller Visby): arn
Ange datum (YYYY-MM-DD / nu / idag / imorgon / igår):
```
- The airport can be given as an IATA code or a city name, case-insensitively.
- The date can be an ISO date or one of the keywords `nu` (now), `idag` (today), `imorgon`
  (tomorrow) and `igår` (yesterday).
- The prompt text differs from the `_choose_airport()` fragment below ("Ange flygplats:"), so the
  fragment is probably from an earlier version.

### Flight list and paging
Flights are printed as cards (layout in "Data model → Flight (as displayed)"), 50 at a time.
After each page:
```
── Visar 50/217 ──  (167 kvar)
[Enter] nästa sida  |  [a] visa alla  |  [q] tillbaka till menyn:
```
That is: showing 50 of 217 (167 left); Enter shows the next page, `a` shows the rest, and `q`
goes back to the menu.

---

## What we know (actual source code functions)

```python
def _choose_airport() -> str:
    while True:
        raw = input("Ange flygplats: ").strip()
        if raw.upper() in AIRPORTS:
            return raw.upper()
        if raw.lower() in _AIRPORT_ALIASES:
            return _AIRPORT_ALIASES[raw.lower()]
        print("Okänd flygplats, försök igen.")
```

```python
def _is_valid_flight(flight: dict) -> bool:
    """Return False for ghost entries where all key fields are empty."""
    has_id     = bool(flight.get("flightId"))
    has_origin = bool(flight.get("departureAirportEnglish") or flight.get("arrivalAirportEnglish"))
    times      = flight.get("arrivalTime") or flight.get("departureTime") or {}
    has_time   = bool(times.get("scheduledUtc"))
    return has_id or has_origin or has_time
```

### Observations from these fragments
- `_choose_airport` calls `input()` and `print()` directly, which makes it hard to test. In the recreation, input/output will be injected.
- `_is_valid_flight` reveals that **the API returns "ghost" entries** with empty fields. Validation therefore belongs in the parsing layer, before data reaches the rest of the program, and is an obvious first unit test.
- The UI text is Swedish while the code is English. The recreation uses an English UI (see Decisions).

---

## Weaknesses in the original (improvement targets)
| Weakness | Planned improvement |
|---|---|
| API key in plaintext in source | Read from environment variable / `.env` (git-ignored); ship `.env.example` |
| One large file with mixed concerns (HTTP, parsing, UI) | Layered package: domain, api, services, cli |
| Hard-wired `input()` / `print()` / HTTP calls | Dependency injection → testable |
| No tests (as far as is known) | Unit and integration tests with fakes and recorded fixtures |
| Ghost entries handled ad hoc | Validation in one place, in the parser |
| Unknown error handling (timeouts, 401, 429) | Explicit error types and user-friendly messages |
| The queried airport's name is blank in the flight card (`To : (ARN)`) | Fill it in from `AIRPORTS` |

---

## Questions

### Q: He mentions a heartbeat in the API health check. How has that been implemented?
> Not shown in the video. Recreated to the best of my ability.

Hypotheses, from most to least likely:
1. **Single ping with latency**: call the health endpoint (or a cheap arrivals request), measure the round-trip time, and print status code + latency.
2. **Repeated ping**: send N requests with an interval (e.g. 5 × every 2 s) and show min/avg/max latency, like `ping`.
3. **Background thread** that polls while the menu runs and shows status in the menu header.

The API has a dedicated `GET /heartBeat` endpoint, so each ping is one call to it, timed by the client. The reference says it returns `{}`, but the real body is the JSON string `"IsAlive"` (task 05), so a ping is judged by its status code, not its body.

**Decision:** implement option 2 with a small N and a configurable interval. It looks like a "heartbeat", stays quota-friendly and is fully testable with an injected clock and a fake source. A background thread (option 3) is not planned.

### Q: What does "run full-auto demo" do?
> Hypothesis: runs every feature in sequence (arrivals, departures, search, OData, health) against a default airport without user input.

**Decision:** recreate it as a scripted sequence of the same service calls the menu uses. Because of DI, the demo can also run in an **offline mode** against recorded fixtures, which is useful for the video and when the quota has run out.

### Q: How is "search a specific flight" implemented?
> The menu label only says "search a specific flight number"; it doesn't mention an airport.
>
> **Decision:** ask for the flight number and a date, then make one OData call with **no airport clause**, so all Swedavia airports are searched: `flightId eq 'SK532' and scheduled eq 'YYMMDD'` (no `flightType`, so arrivals and departures both match). The flight id is normalised (upper case, no spaces) first. If task 05 shows the API needs `airport`, ask for the airport too and add `airport eq '…'`.

### Q: How are dates entered?
> The video shows `YYYY-MM-DD / nu / idag / imorgon / igår`.
>
> **Decision:** accept `YYYY-MM-DD`, `now`, `today`, `tomorrow` and `yesterday` (English UI), plus **empty input = today** (our addition, for speed). Invalid input re-prompts. Used by options 1, 2, 3 and 7. "Today" comes from the injected clock.

### Q: What does option 4 "OData query" let the user do?
> Not shown beyond the menu label.
>
> **Decision:** after choosing an airport and a date, offer a short list of ready-made queries (the API reference examples, filled in with that airport and date: departures, arrivals, a single flight, by status) plus "type your own filter". It is useful for the video and still exposes the raw query endpoint.

### Q: How is destinationer.py reached, and what does 1–3 mean?
> The video shows a script with its own `main()` that runs once. It may also be called from the main menu; the video doesn't settle which. The three choices are most likely arrivals / departures / both (an assumption, not shown).
>
> **Decision (corrected 2026-11-24):** recreate the behaviour, not the file layout, and **keep the menu exactly as in the video: six options**. The overview is offered after options 1 and 2 have listed their flights ("Show destination overview (cities, countries, flight counts)? [y/N]"). `y` asks for the same optional filter as the original and shows the city | country | count table, built from the flights just listed, so it costs no extra API call. The logic lives in `services/destinations.py` (`summarise_destinations`) and `cli/destinations.py`. There is one entry point only.
>
> Consequences: the direction comes from the option (1 arrivals, 2 departures), so the original's "3 both" choice isn't in the UI; `destination_overview(..., Which.BOTH)` still exists as a library function.
>
> *History:* this was first implemented as a seventh menu option. That came from a misunderstanding: Alex's "drop the wrapper" was read as approving the whole proposal (option 7 plus a separate command), when it only rejected the separate command. See PROGRESS.md, "Correction: no menu option 7".

### Q: How was city_country.json built from the Excel file?
> Unknown. **Decision:** write a small, separate build script (`scripts/build_city_country.py`) so the JSON is reproducible instead of hand-made. It is not part of the runtime app.

### Q: What happens when a city is missing from city_country.json?
> Unknown. With a few hundred cities, a destination outside the statistics file (a new route, a charter destination) is realistic. **Decision:** fall back to "Unknown" and count it rather than crashing. Optionally list the unmatched city names, so the JSON can be updated.

### Q: Which aliases exist in `_AIRPORT_ALIASES`?
> Not shown. **Decision:** city names with and without Swedish characters (e.g. `göteborg`, `goteborg`, `malmo`, `arlanda`).

---

## Decisions
| Topic | Decision | Reason |
|---|---|---|
| Language | Python 3.12+ | Same as original; modern typing |
| HTTP library | `httpx` | Built-in `MockTransport` makes the HTTP client testable without network or extra libraries |
| Tests | `pytest` | Fixtures and parametrization fit the testing strategy well |
| Static checks | `ruff` (lint + format), `mypy` (type check) | Consistent style, typed code |
| Config | Environment variable `SWEDAVIA_API_KEY`, loaded from a git-ignored `.env` via `uv run --env-file .env` | No secrets in git; the key never has to be read by tools or typed on a command line |
| Dependency management | `uv` with `pyproject.toml` and `uv.lock` | Fast, one tool for venv, deps and running; locked installs in CI |
| UI language | English | Matches the documentation; better for a portfolio |
| Terminal output | Plain `print` | Keep scope small |
| Quota protection | Short-lived response cache (`CachingFlightSource`) | Avoid repeat calls, e.g. view departures then search |
| Offline mode | `--offline` flag using recorded sample data | Demos and the video without network, key or quota |
| Flight search | One OData query (`flightId`, `scheduled`; no airport) | Half the quota cost of fetching both lists, and finds the flight at any airport |
| Flight card and paging | Same layout as the original (UTC → local, `–`/`N/A`), 50 per page with Enter / `a` / `q` | Faithful to the video; queried airport's name filled in |
| Airport lines on the card | Both as `Name (IATA)`: `London (LHR)`, `Stockholm Arlanda (ARN)`. A code the API already put in the name isn't repeated | The original mixed `London LHR` with a blank `(ARN)`; one consistent format, with the missing name filled in |
| Query size and paging | Always send an explicit `count` (1000); don't use `continuationtoken` | The default of 25 silently truncates results; the token is a change feed, not paging |
| Destinations helper | Offered after options 1 and 2 (y/N), from the flights just listed; menu keeps the original six options; no separate entry point | Faithful menu, no extra API call, one way to start the app |
| Development workflow | Agentic: Claude Code works from task files; Alex reviews and commits | See "Development workflow" in `documentation.md` |
