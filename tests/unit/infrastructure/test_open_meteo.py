from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
import respx

from forecheck.application.catalog import DEFAULT_CATALOG
from forecheck.application.errors import SourceUnavailableError
from forecheck.domain.entities import Station
from forecheck.domain.types import ModelId, Variable
from forecheck.infrastructure.http import HttpClient
from forecheck.infrastructure.open_meteo import FORECAST_URL, PREVIOUS_RUNS_URL, OpenMeteo
from tests.support.fixtures import json_fixture

KRAKOW = next(s for s in DEFAULT_CATALOG.stations if s.name == "Kraków")
ISSUED = datetime(2026, 10, 20, 9, 30, tzinfo=UTC)  # the day the forecast fixture was recorded


def adapter(models: dict[ModelId, str] | None = None) -> OpenMeteo:
    http = HttpClient(user_agent="test", sleep=lambda _: None)
    return OpenMeteo(http, models or DEFAULT_CATALOG.provider_names)


@respx.mock
def test_a_daily_forecast_gives_every_model_variable_and_lead() -> None:
    respx.get(FORECAST_URL).respond(200, json=json_fixture("open_meteo_forecast.json"))
    forecasts = adapter().fetch_forecasts(KRAKOW, ISSUED)

    assert len(forecasts) == 3 * 4 * 7
    assert {f.model for f in forecasts} == {"icon", "ecmwf", "gfs"}
    assert {f.lead_days for f in forecasts} == set(range(1, 8))
    assert all(f.issued_at == ISSUED and f.station_id == KRAKOW.id for f in forecasts)


@respx.mock
def test_a_malformed_value_is_a_source_error_not_a_crash() -> None:
    payload = json_fixture("open_meteo_forecast.json")
    payload["daily"]["temperature_2m_mean_icon_seamless"][1] = "n/a"
    respx.get(FORECAST_URL).respond(200, json=payload)
    with pytest.raises(SourceUnavailableError, match="malformed"):
        adapter().fetch_forecasts(KRAKOW, ISSUED)


@respx.mock
def test_the_request_asks_for_utc_days_in_metres_per_second() -> None:
    route = respx.get(FORECAST_URL).respond(200, json=json_fixture("open_meteo_forecast.json"))
    adapter().fetch_forecasts(KRAKOW, ISSUED)
    params = route.calls.last.request.url.params
    assert params["timezone"] == "UTC"
    assert params["wind_speed_unit"] == "ms"
    assert params["models"] == "icon_seamless,ecmwf_ifs025,gfs_seamless"
    assert params["forecast_days"] == "8"
    assert params["latitude"] == "50.078"


@respx.mock
def test_values_are_read_from_the_right_model_and_variable() -> None:
    payload = json_fixture("open_meteo_forecast.json")
    respx.get(FORECAST_URL).respond(200, json=payload)
    forecasts = adapter().fetch_forecasts(KRAKOW, ISSUED)

    tomorrow = date(2026, 10, 21)
    index = payload["daily"]["time"].index(tomorrow.isoformat())
    ecmwf, gfs, icon = ModelId("ecmwf"), ModelId("gfs"), ModelId("icon")
    expected = {
        (Variable.TEMPERATURE, ecmwf): payload["daily"]["temperature_2m_mean_ecmwf_ifs025"][index],
        (Variable.PRESSURE, gfs): payload["daily"]["pressure_msl_mean_gfs_seamless"][index],
        (Variable.WIND, icon): payload["daily"]["wind_speed_10m_mean_icon_seamless"][index],
        (Variable.PRECIPITATION, icon): payload["daily"]["precipitation_sum_icon_seamless"][index],
    }
    found = {(f.variable, f.model): f.value for f in forecasts if f.valid_date == tomorrow}
    for key, value in expected.items():
        assert found[key] == value


@respx.mock
def test_the_chance_of_rain_is_a_share_and_belongs_to_precipitation_only() -> None:
    payload = json_fixture("open_meteo_forecast.json")
    respx.get(FORECAST_URL).respond(200, json=payload)
    forecasts = adapter().fetch_forecasts(KRAKOW, ISSUED)

    wet = [f for f in forecasts if f.variable is Variable.PRECIPITATION]
    assert all(f.probability is not None and 0.0 <= f.probability <= 1.0 for f in wet)
    assert all(f.probability is None for f in forecasts if f.variable is not Variable.PRECIPITATION)
    raw = payload["daily"]["precipitation_probability_max_ecmwf_ifs025"][2]  # 2026-10-22
    chosen = next(f for f in wet if f.model == "ecmwf" and f.valid_date == date(2026, 10, 22))
    assert chosen.probability == pytest.approx(raw / 100)


@respx.mock
def test_the_day_the_forecast_is_issued_is_not_a_forecast() -> None:
    respx.get(FORECAST_URL).respond(200, json=json_fixture("open_meteo_forecast.json"))
    forecasts = adapter().fetch_forecasts(KRAKOW, ISSUED)
    assert date(2026, 10, 20) not in {f.valid_date for f in forecasts}


@respx.mock
def test_a_missing_value_is_skipped_not_invented() -> None:
    payload = json_fixture("open_meteo_forecast.json")
    payload["daily"]["temperature_2m_mean_gfs_seamless"][1] = None
    respx.get(FORECAST_URL).respond(200, json=payload)
    forecasts = adapter().fetch_forecasts(KRAKOW, ISSUED)
    assert len(forecasts) == 3 * 4 * 7 - 1


@respx.mock
def test_a_single_model_response_has_unsuffixed_keys() -> None:
    payload = json_fixture("open_meteo_forecast.json")
    single = {"daily": {"time": payload["daily"]["time"]}}
    for variable in (
        "temperature_2m_mean",
        "precipitation_sum",
        "precipitation_probability_max",
        "wind_speed_10m_mean",
        "pressure_msl_mean",
    ):
        single["daily"][variable] = payload["daily"][f"{variable}_ecmwf_ifs025"]
    respx.get(FORECAST_URL).respond(200, json=single)
    forecasts = adapter({ModelId("ecmwf"): "ecmwf_ifs025"}).fetch_forecasts(KRAKOW, ISSUED)
    assert len(forecasts) == 4 * 7
    assert {f.model for f in forecasts} == {"ecmwf"}


@respx.mock
def test_a_response_without_a_daily_section_is_an_error() -> None:
    respx.get(FORECAST_URL).respond(200, json={"error": False})
    with pytest.raises(SourceUnavailableError, match="daily"):
        adapter().fetch_forecasts(KRAKOW, ISSUED)


@respx.mock
def test_archived_forecasts_are_rebuilt_from_hourly_series() -> None:
    payload = json_fixture("open_meteo_previous_runs_hourly.json")
    route = respx.get(PREVIOUS_RUNS_URL).respond(200, json=payload)
    forecasts = adapter().fetch_archived_forecasts(KRAKOW, date(2026, 9, 1), date(2026, 9, 2))

    request = route.calls.last.request.url.params
    assert "temperature_2m_previous_day1" in request["hourly"]
    assert "pressure_msl_previous_day7" in request["hourly"]
    assert "daily" not in request

    # The recorded response holds 5 of the 28 series per model, over two days. ICON has no
    # pressure at a lead of 7 days in the archive (all null), so those two days are skipped.
    assert len(forecasts) == 5 * 2 * 3 - 2
    chosen = next(
        f
        for f in forecasts
        if f.model == "ecmwf"
        and f.variable is Variable.TEMPERATURE
        and f.lead_days == 3
        and f.valid_date == date(2026, 9, 1)
    )
    hours = payload["hourly"]["temperature_2m_previous_day3_ecmwf_ifs025"][:24]
    assert chosen.value == pytest.approx(sum(hours) / 24)
    assert chosen.issued_at == datetime(2026, 8, 29, 0, 0, tzinfo=UTC)


@respx.mock
def test_archived_precipitation_is_the_sum_of_the_day() -> None:
    payload = json_fixture("open_meteo_previous_runs_hourly.json")
    respx.get(PREVIOUS_RUNS_URL).respond(200, json=payload)
    forecasts = adapter().fetch_archived_forecasts(KRAKOW, date(2026, 9, 1), date(2026, 9, 2))
    chosen = next(
        f
        for f in forecasts
        if f.model == "icon"
        and f.variable is Variable.PRECIPITATION
        and f.valid_date == date(2026, 9, 2)
    )
    hours = payload["hourly"]["precipitation_previous_day1_icon_seamless"][24:48]
    assert chosen.value == pytest.approx(sum(hours))


@respx.mock
def test_a_long_archive_range_is_requested_in_chunks() -> None:
    payload = json_fixture("open_meteo_previous_runs_hourly.json")
    route = respx.get(PREVIOUS_RUNS_URL).mock(return_value=httpx.Response(200, json=payload))
    adapter().fetch_archived_forecasts(
        KRAKOW, date(2026, 1, 1), date(2026, 1, 1) + timedelta(days=69)
    )
    ranges = [
        (c.request.url.params["start_date"], c.request.url.params["end_date"]) for c in route.calls
    ]
    assert ranges == [
        ("2026-01-01", "2026-01-31"),
        ("2026-02-01", "2026-03-03"),
        ("2026-03-04", "2026-03-11"),
    ]


def test_the_default_catalog_names_models_the_provider_knows() -> None:
    assert DEFAULT_CATALOG.provider_names == {
        "icon": "icon_seamless",
        "ecmwf": "ecmwf_ifs025",
        "gfs": "gfs_seamless",
    }


def test_station_is_a_plain_value() -> None:
    assert isinstance(KRAKOW, Station)
