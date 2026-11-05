"""Station measurements from IMGW-PIB (https://danepubliczne.imgw.pl).

Data: Instytut Meteorologii i Gospodarki Wodnej - Państwowy Instytut Badawczy, under the
regulation at https://danepubliczne.imgw.pl/regulations (see ``docs/data-sources.md``).

Why the archive and not the live API: ``/api/data/synop`` only ever returns the latest
hourly report, with no history. The hourly synoptic archive (``terminowe/synop``) has every
report, so a UTC day can be rebuilt exactly, at the price of a lag: a month's file appears
about two weeks after the month ends.

File layout, checked against the live server:

- the current year: one zip per month with all stations, ``YYYY_MM_s.zip``;
- earlier years: one zip per station per year, ``YYYY_NNN_s.zip``, where ``NNN`` is the last
  three digits of the station's IMGW id;
- inside, one windows-1250 CSV with no header row; the header is a separate file.
"""

import csv
import io
import re
import zipfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from forecheck.application.errors import NotFoundError, SourceUnavailableError
from forecheck.domain.daily import daily_mean, daily_precipitation
from forecheck.domain.entities import Observation, Station
from forecheck.domain.types import StationId, Variable
from forecheck.infrastructure.http import HttpClient

BASE_URL = "https://danepubliczne.imgw.pl/data/dane_pomiarowo_obserwacyjne/dane_meteorologiczne/terminowe/synop"
HEADER_URL = f"{BASE_URL}/s_t_nag%c5%82%c3%b3wek.csv"
_ENCODING = "cp1250"

# Status flags used by IMGW next to every value.
_NO_MEASUREMENT = "8"
_NO_PHENOMENON = "9"  # for precipitation: it did not rain

_LISTING_ENTRY = re.compile(
    r'<a href="(\d{4}_\d{2,3}_s\.zip)">[^<]*</a>\s*</td><td[^>]*>\s*([\d-]+ [\d:]+)'
)


@dataclass(frozen=True, slots=True)
class _Hour:
    """The reports of one station at one UTC hour that Forecheck uses."""

    temperature: float | None
    wind: float | None
    pressure: float | None
    precipitation_6h: float | None


class ImgwSynopArchive:
    """Implements ``ObservationSource`` from the hourly synoptic archive."""

    def __init__(self, http: HttpClient, base_url: str = BASE_URL) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")
        self._listings: dict[int, dict[str, str]] = {}
        self._columns: dict[str, int] | None = None
        self._zips: dict[str, bytes] = {}
        # Parsed files. A yearly station file serves every month of its year, so it is asked for
        # again and again within one read.
        self._parsed: dict[
            tuple[str, tuple[StationId, ...]], dict[tuple[StationId, date, int], _Hour]
        ] = {}

    # --- ObservationSource -------------------------------------------------------------

    def available_months(
        self, stations: Sequence[Station], start: date, end: date
    ) -> dict[date, str]:
        # A read starts here. The archive object lives as long as a warm serverless instance, so
        # what it fetched for an earlier read must not stand in for the directory as it is now.
        self._listings.clear()
        self._zips.clear()
        self._parsed.clear()
        available: dict[date, str] = {}
        for month in _months(start, end):
            versions = [version for _, version in self._files_for(month, stations)]
            if versions:
                available[month] = max(versions)
        return available

    def fetch_observations(
        self, stations: Sequence[Station], start: date, end: date
    ) -> list[Observation]:
        # Precipitation for a UTC day needs the 00 UTC report of the day after.
        hours: dict[tuple[StationId, date, int], _Hour] = {}
        for month in _months(start, end + timedelta(days=1)):
            for name, _ in self._files_for(month, stations):
                hours.update(self._read(name, stations))

        observations: list[Observation] = []
        day = start
        while day <= end:
            for station in stations:
                observations.extend(_observations_for_day(station.id, day, hours))
            day += timedelta(days=1)
        return observations

    # --- files -------------------------------------------------------------------------

    def _listing(self, year: int) -> dict[str, str]:
        if year not in self._listings:
            html = self._http.get_text(f"{self._base_url}/{year}/")
            self._listings[year] = dict(_LISTING_ENTRY.findall(html))
        return self._listings[year]

    def _files_for(self, month: date, stations: Sequence[Station]) -> list[tuple[str, str]]:
        """The zip files holding ``month`` for ``stations``, as (path, version)."""
        try:
            listing = self._listing(month.year)
        except NotFoundError:
            # A year with no directory yet (the future) simply has no data. Any other failure
            # propagates: an outage must not look like "nothing published".
            return []
        monthly = f"{month.year}_{month.month:02d}_s.zip"
        if monthly in listing:
            return [(f"{month.year}/{monthly}", listing[monthly])]
        per_station = [f"{month.year}_{_code(station)}_s.zip" for station in stations]
        return [(f"{month.year}/{name}", listing[name]) for name in per_station if name in listing]

    def _read(
        self, path: str, stations: Sequence[Station]
    ) -> dict[tuple[StationId, date, int], _Hour]:
        cache_key = (path, tuple(station.id for station in stations))
        if cache_key not in self._parsed:
            self._parsed[cache_key] = self._parse(path, stations)
        return self._parsed[cache_key]

    def _parse(
        self, path: str, stations: Sequence[Station]
    ) -> dict[tuple[StationId, date, int], _Hour]:
        if path not in self._zips:
            self._zips[path] = self._http.get_bytes(f"{self._base_url}/{path}")
        columns = self._header()
        by_code = {_code(station): station.id for station in stations}

        try:
            with zipfile.ZipFile(io.BytesIO(self._zips[path])) as archive:
                raw = archive.read(archive.namelist()[0]).decode(_ENCODING)
        except (zipfile.BadZipFile, IndexError, UnicodeDecodeError) as error:
            raise SourceUnavailableError(f"{path} is not a readable IMGW archive") from error

        hours: dict[tuple[StationId, date, int], _Hour] = {}
        for row in csv.reader(io.StringIO(raw)):
            if len(row) != len(columns):
                continue
            station_id = by_code.get(row[columns["NSP"]][-3:])
            if station_id is None:
                continue
            day = date(int(row[columns["ROK"]]), int(row[columns["MC"]]), int(row[columns["DZ"]]))
            hour = int(row[columns["GG"]])
            hours[(station_id, day, hour)] = _Hour(
                temperature=_measured(row, columns, "TEMP"),
                wind=_measured(row, columns, "FWR"),
                pressure=_measured(row, columns, "PPPM"),
                precipitation_6h=_precipitation(row, columns),
            )
        return hours

    def _header(self) -> dict[str, int]:
        if self._columns is None:
            text = self._http.get_text(
                HEADER_URL if self._base_url == BASE_URL else f"{self._base_url}/header.csv"
            )
            names = next(csv.reader(io.StringIO(text.strip())), [])
            columns = {name: index for index, name in enumerate(names)}
            needed = {
                "NSP",
                "ROK",
                "MC",
                "DZ",
                "GG",
                "TEMP",
                "WTEMP",
                "FWR",
                "WFWR",
                "PPPM",
                "WPPPM",
                "WO6G",
                "WWO6G",
            }
            if not needed <= columns.keys():
                raise SourceUnavailableError(
                    f"IMGW header lacks columns {sorted(needed - columns.keys())}"
                )
            self._columns = columns
        return self._columns


def _code(station: Station) -> str:
    """The three digits that tell a station apart in archive file and row names."""
    return station.id[-3:]


def _months(start: date, end: date) -> Iterable[date]:
    month = start.replace(day=1)
    while month <= end:
        yield month
        month = (month + timedelta(days=32)).replace(day=1)


def _number(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _measured(row: list[str], columns: dict[str, int], name: str) -> float | None:
    """A value is usable when it is present and its status is not "no measurement"."""
    if row[columns[f"W{name}"]] == _NO_MEASUREMENT:
        return None
    return _number(row[columns[name]])


def _precipitation(row: list[str], columns: dict[str, int]) -> float | None:
    """The six-hour total reported at 00, 06, 12 and 18 UTC. "No phenomenon" is a dry spell."""
    status = row[columns["WWO6G"]]
    if status == _NO_PHENOMENON:
        return 0.0
    if status == _NO_MEASUREMENT:
        return None
    return _number(row[columns["WO6G"]])


def _observations_for_day(
    station_id: StationId, day: date, hours: dict[tuple[StationId, date, int], _Hour]
) -> list[Observation]:
    reports = [hours.get((station_id, day, hour)) for hour in range(24)]
    series = {
        Variable.TEMPERATURE: [report.temperature if report else None for report in reports],
        Variable.WIND: [report.wind if report else None for report in reports],
        Variable.PRESSURE: [report.pressure if report else None for report in reports],
    }
    found: list[Observation] = []
    for variable, values in series.items():
        mean = daily_mean(values)
        if mean is not None:
            found.append(Observation(station_id, variable, day, mean))

    next_day = day + timedelta(days=1)
    totals = {
        6: _total(hours, station_id, day, 6),
        12: _total(hours, station_id, day, 12),
        18: _total(hours, station_id, day, 18),
        24: _total(hours, station_id, next_day, 0),
    }
    precipitation = daily_precipitation(totals)
    if precipitation is not None:
        found.append(Observation(station_id, Variable.PRECIPITATION, day, precipitation))
    return found


def _total(
    hours: dict[tuple[StationId, date, int], _Hour], station_id: StationId, day: date, hour: int
) -> float | None:
    report = hours.get((station_id, day, hour))
    return report.precipitation_6h if report else None
