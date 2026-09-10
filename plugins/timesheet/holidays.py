"""OpenHolidays API client + on-disk cache (r-10.md).

https://openholidaysapi.org — free, no API key. Used for two things:
  - the country picker in settings (fetch_countries)
  - the actual public-holiday dates for a given country/year, which the
    summary/PDF computation excludes from "working days" the same way a
    weekend already is.

Network calls are synchronous stdlib urllib (no new dependency — same
"ask before adding one" bar already applied to the PDF-generation choice)
with a short timeout, wrapped so a network failure degrades to "no
holidays known" rather than crashing anything. Results are cached to disk
so a window works offline after the first successful fetch, and doesn't
re-hit the API on every plugin load.
"""
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
    """[{"code": "SK", "name": "Slovakia"}, ...] — every country the API
    knows holidays for. Empty list (not an exception) on any network
    failure, so a settings dialog can still render, just with no choices
    yet."""
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
    """OpenHolidays gives startDate/endDate per holiday — usually the same
    single day, occasionally a real range (e.g. a multi-day regional
    holiday) — expanded here into individual "YYYY-MM-DD" strings so a
    plain `date in holiday_dates` set membership check covers both cases
    identically."""
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
    """{"YYYY-MM-DD": "Holiday name", ...} for every public holiday in the
    given country and calendar year. Empty dict on any network failure or
    an unset country_code."""
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
    """Read-through cache: a hit returns straight from disk, a miss fetches
    from the API and writes the cache file (even an empty result, so a
    genuinely holiday-free country/year — or a year the API doesn't cover
    — doesn't get re-fetched every time either). refresh_holidays() below
    is the only way to force a re-fetch."""
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
    """Forces a re-fetch by deleting the cache entry first — explicit,
    user-triggered ("Refresh holidays" in settings), no time-based expiry
    logic to get subtly wrong."""
    path = _cache_path(cache_dir, country_code, year)
    if os.path.exists(path):
        os.remove(path)
    return get_holidays(cache_dir, country_code, year)


class HolidaysProvider(QObject):
    """Thin QML-facing wrapper around this module's plain functions, bound
    to one window's own cache directory — exposed as a context property
    (plugin.py's create_content) so QML can populate the country picker
    and read holiday dates without any of this module's plumbing details."""

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
