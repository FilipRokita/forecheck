from datetime import date

import httpx
import pytest
import respx

from forecheck.application.catalog import DEFAULT_CATALOG
from forecheck.application.errors import SourceUnavailableError
from forecheck.domain.entities import Station
from forecheck.domain.types import StationId, Variable
from forecheck.infrastructure.http import HttpClient
from forecheck.infrastructure.imgw import BASE_URL, HEADER_URL, ImgwSynopArchive
from tests.support.fixtures import (
    bytes_fixture,
    imgw_archive,
    imgw_hour,
    imgw_rows,
    text_fixture,
)

KRAKOW = next(s for s in DEFAULT_CATALOG.stations if s.name == "Kraków")
RZESZOW = next(s for s in DEFAULT_CATALOG.stations if s.name == "Rzeszów")
SAMPLE = bytes_fixture("imgw_terminowe_synop_sample.zip")
MONTH_URL = f"{BASE_URL}/2026/2026_09_s.zip"


def archive() -> ImgwSynopArchive:
    return ImgwSynopArchive(HttpClient(user_agent="test", sleep=lambda _: None))


def serve_sample() -> None:
    respx.get(HEADER_URL).respond(200, text=text_fixture("imgw_terminowe_header.csv"))
    respx.get(f"{BASE_URL}/2026/").respond(200, text=text_fixture("imgw_listing_sample.html"))
    respx.get(MONTH_URL).respond(200, content=SAMPLE)


@respx.mock
def test_a_published_month_is_available_with_its_publication_time_as_version() -> None:
    serve_sample()
    months = archive().available_months([KRAKOW], date(2026, 8, 15), date(2026, 10, 20))
    assert months[date(2026, 9, 1)] == "2026-10-16 10:06"
    assert date(2026, 10, 1) not in months  # October is not published yet


@respx.mock
def test_a_second_read_sees_months_published_since_the_first() -> None:
    def listing(*months: str) -> httpx.Response:
        entries = "".join(
            f'<tr><td><a href="2026_{m}_s.zip">x</a></td><td>2026-{m}-16 10:06</td></tr>'
            for m in months
        )
        return httpx.Response(200, text=f"<table>{entries}</table>")

    respx.get(f"{BASE_URL}/2026/").mock(side_effect=[listing("09"), listing("09", "10")])
    source = archive()
    assert date(2026, 10, 1) not in source.available_months(
        [KRAKOW], date(2026, 9, 1), date(2026, 10, 31)
    )
    assert date(2026, 10, 1) in source.available_months(
        [KRAKOW], date(2026, 9, 1), date(2026, 10, 31)
    )


@respx.mock
def test_a_year_without_a_directory_has_no_months() -> None:
    respx.get(f"{BASE_URL}/2027/").respond(404)
    assert archive().available_months([KRAKOW], date(2027, 1, 1), date(2027, 3, 1)) == {}


@respx.mock
def test_an_outage_is_an_error_not_an_empty_archive() -> None:
    respx.get(f"{BASE_URL}/2026/").respond(503)
    with pytest.raises(SourceUnavailableError):
        archive().available_months([KRAKOW], date(2026, 9, 1), date(2026, 9, 30))


@respx.mock
def test_real_station_days_become_one_figure_per_variable() -> None:
    serve_sample()
    found = archive().fetch_observations([KRAKOW, RZESZOW], date(2026, 9, 1), date(2026, 9, 3))

    assert len(found) == 2 * 3 * 4
    assert {o.variable for o in found} == set(Variable)
    assert {o.station_id for o in found} == {KRAKOW.id, RZESZOW.id}


@respx.mock
def test_a_daily_mean_matches_the_hourly_rows_it_is_made_of() -> None:
    serve_sample()
    rows = [r for r in imgw_rows(SAMPLE) if r["NSP"].endswith("566") and r["DZ"] == "02"]
    assert len(rows) == 24
    expected = sum(float(r["TEMP"]) for r in rows) / 24

    found = archive().fetch_observations([KRAKOW], date(2026, 9, 2), date(2026, 9, 2))
    temperature = next(o for o in found if o.variable is Variable.TEMPERATURE)
    assert temperature.value == pytest.approx(expected)
    assert temperature.day == date(2026, 9, 2)


@respx.mock
def test_real_values_have_the_units_the_forecasts_use() -> None:
    serve_sample()
    found = archive().fetch_observations([KRAKOW], date(2026, 9, 1), date(2026, 9, 3))
    by_variable = {v: [o.value for o in found if o.variable is v] for v in Variable}
    assert all(-30 < t < 45 for t in by_variable[Variable.TEMPERATURE])
    assert all(950 < p < 1060 for p in by_variable[Variable.PRESSURE])  # sea level, hPa
    assert all(0 <= w < 30 for w in by_variable[Variable.WIND])  # m/s
    assert all(0 <= r < 300 for r in by_variable[Variable.PRECIPITATION])  # mm


def day_rows(nsp: str, day: str, *, temp: str = "10.0") -> list[dict[str, str]]:
    return [imgw_hour(nsp, day, hour, temp=temp) for hour in range(24)]


def serve_synthetic(rows: list[dict[str, str]]) -> None:
    respx.get(HEADER_URL).respond(200, text=text_fixture("imgw_terminowe_header.csv"))
    respx.get(f"{BASE_URL}/2026/").respond(200, text=text_fixture("imgw_listing_sample.html"))
    respx.get(MONTH_URL).respond(200, content=imgw_archive(rows))


@respx.mock
def test_precipitation_adds_the_four_six_hour_reports_of_the_utc_day() -> None:
    rows = day_rows("350190566", "2026-09-05") + day_rows("350190566", "2026-09-06")
    for row in rows:
        row["WWO6G"] = "8"  # "no measurement" except at the reporting hours below
    reports = {
        ("2026-09-05", 6): "0.5",
        ("2026-09-05", 12): "1.0",
        ("2026-09-05", 18): "0.0",
        ("2026-09-06", 0): "2.0",
    }
    for row in rows:
        key = (f"{row['ROK']}-{row['MC']}-{row['DZ']}", int(row["GG"]))
        if key in reports:
            row["WO6G"], row["WWO6G"] = reports[key], ""
    # "No phenomenon" (status 9) at 18 UTC is a dry six hours, not a gap.
    next(r for r in rows if (r["DZ"], r["GG"]) == ("05", "18"))["WWO6G"] = "9"
    next(r for r in rows if (r["DZ"], r["GG"]) == ("05", "18"))["WO6G"] = ""

    serve_synthetic(rows)
    found = archive().fetch_observations([KRAKOW], date(2026, 9, 5), date(2026, 9, 5))
    rain = next(o for o in found if o.variable is Variable.PRECIPITATION)
    assert rain.value == pytest.approx(3.5)


@respx.mock
def test_precipitation_is_left_out_when_a_report_is_missing() -> None:
    rows = day_rows("350190566", "2026-09-05")  # no report for 00 UTC of the 6th at all
    for row in rows:
        row["WWO6G"] = "9"
    serve_synthetic(rows)
    found = archive().fetch_observations([KRAKOW], date(2026, 9, 5), date(2026, 9, 5))
    assert Variable.PRECIPITATION not in {o.variable for o in found}
    assert Variable.TEMPERATURE in {o.variable for o in found}


@respx.mock
def test_a_day_with_too_many_missing_hours_is_left_out() -> None:
    rows = day_rows("350190566", "2026-09-05")
    for row in rows[:6]:  # six missing hours, fewer than 20 reports remain
        row["TEMP"], row["WTEMP"] = "", "8"
    serve_synthetic(rows)
    found = archive().fetch_observations([KRAKOW], date(2026, 9, 5), date(2026, 9, 5))
    assert Variable.TEMPERATURE not in {o.variable for o in found}
    assert Variable.WIND in {o.variable for o in found}


@respx.mock
def test_other_stations_in_the_same_file_are_ignored() -> None:
    rows = day_rows("350190566", "2026-09-05", temp="10.0") + day_rows(
        "349190600", "2026-09-05", temp="30.0"
    )
    serve_synthetic(rows)
    found = archive().fetch_observations([KRAKOW], date(2026, 9, 5), date(2026, 9, 5))
    temperature = next(o for o in found if o.variable is Variable.TEMPERATURE)
    assert temperature.value == pytest.approx(10.0)


@respx.mock
def test_earlier_years_come_from_per_station_yearly_files() -> None:
    listing = (
        '<a href="2025_566_s.zip">2025_566_s.zip</a></td><td align="right">2026-02-17 08:52  </td>'
        '<a href="2025_580_s.zip">2025_580_s.zip</a></td><td align="right">2026-02-17 09:10  </td>'
    )
    respx.get(HEADER_URL).respond(200, text=text_fixture("imgw_terminowe_header.csv"))
    respx.get(f"{BASE_URL}/2025/").respond(200, text=listing)
    respx.get(f"{BASE_URL}/2025/2025_566_s.zip").respond(
        200,
        content=imgw_archive(
            day_rows("350190566", "2025-03-04") + day_rows("350190566", "2025-03-05")
        ),
    )

    source = archive()
    months = source.available_months([KRAKOW], date(2025, 3, 1), date(2025, 3, 31))
    assert months == {date(2025, 3, 1): "2026-02-17 08:52"}
    found = source.fetch_observations([KRAKOW], date(2025, 3, 4), date(2025, 3, 4))
    assert {o.variable for o in found} >= {Variable.TEMPERATURE, Variable.WIND, Variable.PRESSURE}


@respx.mock
def test_an_unreadable_archive_is_reported() -> None:
    respx.get(HEADER_URL).respond(200, text=text_fixture("imgw_terminowe_header.csv"))
    respx.get(f"{BASE_URL}/2026/").respond(200, text=text_fixture("imgw_listing_sample.html"))
    respx.get(MONTH_URL).respond(200, content=b"not a zip")
    with pytest.raises(SourceUnavailableError, match="not a readable"):
        archive().fetch_observations([KRAKOW], date(2026, 9, 1), date(2026, 9, 1))


@respx.mock
def test_a_header_without_the_columns_we_need_is_reported() -> None:
    respx.get(HEADER_URL).respond(200, text="NSP,POST,ROK\r\n")
    respx.get(f"{BASE_URL}/2026/").respond(200, text=text_fixture("imgw_listing_sample.html"))
    respx.get(MONTH_URL).respond(200, content=SAMPLE)
    with pytest.raises(SourceUnavailableError, match="lacks columns"):
        archive().fetch_observations([KRAKOW], date(2026, 9, 1), date(2026, 9, 1))


@respx.mock
def test_each_archive_file_is_downloaded_once_per_run() -> None:
    serve_sample()
    route = respx.get(MONTH_URL).mock(return_value=httpx.Response(200, content=SAMPLE))
    source = archive()
    source.fetch_observations([KRAKOW], date(2026, 9, 1), date(2026, 9, 1))
    source.fetch_observations([RZESZOW], date(2026, 9, 2), date(2026, 9, 2))
    assert route.call_count == 1


def test_every_catalog_station_has_a_distinct_archive_code() -> None:
    codes = [s.id[-3:] for s in DEFAULT_CATALOG.stations]
    assert len(set(codes)) == len(codes)


def test_a_station_id_is_a_station_id() -> None:
    assert isinstance(KRAKOW, Station)
    assert KRAKOW.id == StationId("12566")
