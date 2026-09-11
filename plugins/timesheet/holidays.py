from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from PySide6.QtCore import QObject, Slot

_API_BASE = "https://openholidaysapi.org"
_TIMEOUT_SECONDS = 5


def _get_json(url: str):
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_countries() -> list[dict]:
    try:
        raw = _get_json(f"{_API_BASE}/Countries?languageIsoCode=EN")
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return []
    result = []
    for entry in raw:
        names = entry.get("name", [])
        label = names[0]["text"] if names else entry.get("isoCode", "")
        result.append({"code": entry.get("isoCode", ""), "name": label})
    return result


def _expand_date_range(start_iso: str, end_iso: str) -> list[str]:
    from datetime import date, timedelta  # noqa: PLC0415

    start = date.fromisoformat(start_iso)
    end = date.fromisoformat(end_iso)
    dates = []
    cursor = start
    while cursor <= end:
        dates.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return dates


def fetch_holidays(country_code: str, year: int) -> dict[str, str]:
    if not country_code:
        return {}
    url = (
        f"{_API_BASE}/PublicHolidays?countryIsoCode={country_code}"
        f"&languageIsoCode=EN&validFrom={year}-01-01&validTo={year}-12-31"
    )
    try:
        raw = _get_json(url)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return {}
    result = {}
    for entry in raw:
        names = entry.get("name", [])
        label = names[0]["text"] if names else ""
        for day in _expand_date_range(entry["startDate"], entry["endDate"]):
            result[day] = label
    return result


def _cache_path(cache_dir: str, country_code: str, year: int) -> str:
    return os.path.join(cache_dir, f"{country_code}-{year}.json")


def get_holidays(cache_dir: str, country_code: str, year: int) -> dict[str, str]:
    if not country_code:
        return {}
    path = _cache_path(cache_dir, country_code, year)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    holidays = fetch_holidays(country_code, year)
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(holidays, f, indent=2)
    return holidays


def refresh_holidays(cache_dir: str, country_code: str, year: int) -> dict[str, str]:
    path = _cache_path(cache_dir, country_code, year)
    if os.path.exists(path):
        os.remove(path)
    return get_holidays(cache_dir, country_code, year)


class HolidaysProvider(QObject):
    def __init__(self, cache_dir: str, parent=None):
        super().__init__(parent)
        self._cache_dir = cache_dir

    @Slot(result="QVariant")
    def countries(self):
        return fetch_countries()

    @Slot(str, int, result="QVariant")
    def holidaysFor(self, country_code: str, year: int):
        return get_holidays(self._cache_dir, country_code, year)

    @Slot(str, int, result="QVariant")
    def refreshHolidaysFor(self, country_code: str, year: int):
        return refresh_holidays(self._cache_dir, country_code, year)
