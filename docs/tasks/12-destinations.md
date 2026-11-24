# 12 – Destination statistics (destinationer.py equivalent)
Status: done
Owner: agent (Alex provides the data file)
Depends on: 04, 07

## Goal
Recreate the helper that lists every unique city with its country and flight count, filterable
by country or city. This task covers the data and the service only; the interactive flow and the
menu hook (option 7) are in task 13b.

## Before starting
The Swedavia statistics file is in place: `data/raw/destinations-statistik-2025.xlsx` (Alex has
the Excel, not the original JSON, so the build-script route is the one used).
Adding `openpyxl` as a dev dependency (`uv add --dev openpyxl`) needs Alex's approval.

## Context
- `docs/research.md` → "destinationer.py", "city_country.json", **"The statistics file we have"** (sheets, subtotal rows, placeholders, spelling; why 263/59 doesn't apply), Qs about missing cities and the build process
- `docs/research.md` → "How is destinationer.py reached": the original takes airport, date, an optional filter and a 1–3 choice (arrivals / departures / both)

## Acceptance criteria
- [x] `scripts/build_city_country.py` builds `src/flightboard/data/city_country.json` from the `land-fpl` sheet: every country/city pair, skipping `Summa` subtotal rows and the `(tom)` / `UNKNOWN` placeholders, and printing the city and country counts it wrote (`openpyxl` as a dev dependency). Rerunning it gives the same file. The counts go in PROGRESS.md
- [x] `data/lookup.py`: `CityCountryLookup` built from an injected mapping, with name normalisation (case, whitespace, å/ä/ö) matching how the API spells cities
- [x] `services/destinations.py`: from a `FlightSource`, airport, date and direction (arrivals / departures / both), returns rows of (city, country, count) sorted by count desc; filters by country and/or city substring; unmatched cities become country `"Unknown"` and are also listed separately
- [x] Tests: counting, "both" merges arrival and departure counts, filters, Unknown fallback, normalisation; a data test that the shipped JSON has the counts the build script reported, no empty keys or values, no `Summa`/`(tom)`/`UNKNOWN` entries, and contains known cities (e.g. Tirana → ALBANIA, Vienna → AUSTRIA). The original's 263/59 doesn't apply to the 2025 file (see research.md)

## Out of scope
Prompts and menu wiring (task 13b).

## Notes
- Built from `land-fpl`: **345 cities in 67 countries**. Rebuilding gives byte-identical output (keys sorted).
- Dev dependencies `openpyxl` + `types-openpyxl` (approved by Alex; the stubs are needed because mypy checks `scripts/`).
- The JSON is pure Excel data; the API→Excel alias table (`CITY_ALIASES`, 11 entries) lives in `data/lookup.py`. With it, every city in the recorded fixtures resolves except the literal "Unknown".
- **Filter reading:** the criterion's "country and/or city substring" is implemented as ONE substring that matches city OR country, faithful to the original's single `Filter?` prompt. Filtering city AND country at the same time isn't possible (the original couldn't either).
- `fold()` in `domain/airports.py` was made public so the lookup and the service reuse the same accent folding.
