"""Build `city_country.json` from Swedavia's destination statistics (Excel).

Not part of the running app. Rerun it when a new statistics file arrives:

    uv run python -m scripts.build_city_country

It reads the `land-fpl` sheet and writes every (city -> country) pair, skipping subtotal rows
and placeholders. The output has sorted keys, so rerunning on the same file gives the same bytes.
"""

import json
from collections.abc import Iterable
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "raw" / "destinations-statistik-2025.xlsx"
TARGET = ROOT / "src" / "flightboard" / "data" / "city_country.json"
SHEET = "land-fpl"
HEADER_ROWS = 6
PLACEHOLDERS = {"(tom)", "UNKNOWN"}


def city_country_pairs(rows: Iterable[tuple[object, ...]]) -> dict[str, str]:
    """`{city: country}` from the sheet's rows (country, city, airport, ...)."""
    pairs: dict[str, str] = {}
    for row in list(rows)[HEADER_ROWS:]:
        country, city = (_cell(row, 0), _cell(row, 1))
        if not country or not city:
            continue
        if "Summa" in country or "Summa" in city or {country, city} & PLACEHOLDERS:
            continue
        if pairs.get(city, country) != country:
            raise ValueError(f"{city} is listed under both {pairs[city]} and {country}")
        pairs[city] = country
    return pairs


def _cell(row: tuple[object, ...], index: int) -> str:
    value = row[index] if index < len(row) else None
    return str(value).strip() if value is not None else ""


def main() -> None:
    workbook = load_workbook(SOURCE, read_only=True, data_only=True)
    pairs = city_country_pairs(workbook[SHEET].iter_rows(values_only=True))
    TARGET.write_text(
        json.dumps(dict(sorted(pairs.items())), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(pairs)} cities in {len(set(pairs.values()))} countries to {TARGET}")


if __name__ == "__main__":
    main()
