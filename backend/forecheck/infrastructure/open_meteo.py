"""Forecasts from Open-Meteo (https://open-meteo.com), under CC BY 4.0.

Two endpoints, one adapter each:

- the forecast API, called every day for the coming week (``fetch_forecasts``);
- the Previous Runs API, which replays forecasts at a fixed lead of 1 to 7 days
  (``fetch_archived_forecasts``), used once to start with a history.
"""

from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from forecheck.application.errors import SourceUnavailableError
from forecheck.domain.daily import daily_mean, daily_total
from forecheck.domain.entities import Forecast, Station
from forecheck.domain.types import MAX_LEAD_DAYS, MIN_LEAD_DAYS, ModelId, Variable
from forecheck.infrastructure.http import HttpClient

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"

# The forecast API gives daily figures directly.
_DAILY = {
    Variable.TEMPERATURE: "temperature_2m_mean",
    Variable.PRECIPITATION: "precipitation_sum",
    Variable.WIND: "wind_speed_10m_mean",
    Variable.PRESSURE: "pressure_msl_mean",
}
_PROBABILITY = "precipitation_probability_max"

# The Previous Runs API only accepts hourly variables (a daily one is rejected with HTTP 400),
# so a day is rebuilt from its 24 hours.
_HOURLY = {
    Variable.TEMPERATURE: "temperature_2m",
    Variable.PRECIPITATION: "precipitation",
    Variable.WIND: "wind_speed_10m",
    Variable.PRESSURE: "pressure_msl",
}

# Requests are kept small: Open-Meteo weighs a call by variables times days.
_ARCHIVE_CHUNK_DAYS = 31


class OpenMeteo:
    """Implements ``ForecastSource`` and ``ForecastArchive``."""

    def __init__(self, http: HttpClient, models: Mapping[ModelId, str]) -> None:
        self._http = http
        self._models = dict(models)

    def fetch_forecasts(self, station: Station, issued_at: datetime) -> list[Forecast]:
        params: dict[str, str | int | float] = {
            "latitude": station.latitude,
            "longitude": station.longitude,
            "daily": ",".join([*_DAILY.values(), _PROBABILITY]),
            "models": ",".join(self._models.values()),
            "forecast_days": MAX_LEAD_DAYS + 1,
            "timezone": "UTC",
            "wind_speed_unit": "ms",
        }
        daily = _section(self._http.get_json(FORECAST_URL, params), "daily")
        days = [date.fromisoformat(day) for day in _strings(daily, "time")]

        forecasts: list[Forecast] = []
        for model, provider_name in self._models.items():
            probabilities = _series(
                daily, _PROBABILITY, provider_name, len(self._models), len(days)
            )
            for variable, parameter in _DAILY.items():
                values = _series(daily, parameter, provider_name, len(self._models), len(days))
                for index, (day, value) in enumerate(zip(days, values, strict=True)):
                    lead = (day - issued_at.astimezone(UTC).date()).days
                    if value is None or not MIN_LEAD_DAYS <= lead <= MAX_LEAD_DAYS:
                        continue
                    chance = probabilities[index] if variable is Variable.PRECIPITATION else None
                    forecasts.append(
                        Forecast(
                            station_id=station.id,
                            model=model,
                            variable=variable,
                            valid_date=day,
                            issued_at=issued_at,
                            value=value,
                            probability=None
                            if chance is None
                            else min(max(chance / 100.0, 0.0), 1.0),
                        )
                    )
        return forecasts

    def fetch_archived_forecasts(self, station: Station, start: date, end: date) -> list[Forecast]:
        forecasts: list[Forecast] = []
        chunk_start = start
        while chunk_start <= end:
            chunk_end = min(end, chunk_start + timedelta(days=_ARCHIVE_CHUNK_DAYS - 1))
            forecasts.extend(self._archive_chunk(station, chunk_start, chunk_end))
            chunk_start = chunk_end + timedelta(days=1)
        return forecasts

    def _archive_chunk(self, station: Station, start: date, end: date) -> list[Forecast]:
        leads = range(MIN_LEAD_DAYS, MAX_LEAD_DAYS + 1)
        params: dict[str, str | int | float] = {
            "latitude": station.latitude,
            "longitude": station.longitude,
            "hourly": ",".join(
                f"{name}_previous_day{lead}" for name in _HOURLY.values() for lead in leads
            ),
            "models": ",".join(self._models.values()),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "timezone": "UTC",
            "wind_speed_unit": "ms",
        }
        hourly = _section(self._http.get_json(PREVIOUS_RUNS_URL, params), "hourly")
        times = [datetime.fromisoformat(stamp) for stamp in _strings(hourly, "time")]

        by_day: dict[date, list[int]] = defaultdict(list)
        for index, stamp in enumerate(times):
            by_day[stamp.date()].append(index)

        forecasts: list[Forecast] = []
        for model, provider_name in self._models.items():
            for variable, name in _HOURLY.items():
                for lead in leads:
                    values = _series(
                        hourly,
                        f"{name}_previous_day{lead}",
                        provider_name,
                        len(self._models),
                        len(times),
                    )
                    for day, indexes in by_day.items():
                        day_values = [values[index] for index in indexes]
                        total = (
                            daily_total(day_values)
                            if variable is Variable.PRECIPITATION
                            else daily_mean(day_values)
                        )
                        if total is None:
                            continue
                        forecasts.append(
                            Forecast(
                                station_id=station.id,
                                model=model,
                                variable=variable,
                                valid_date=day,
                                # "Previous day N" is the run issued N days before the day.
                                issued_at=datetime.combine(
                                    day - timedelta(days=lead), time(0, 0), UTC
                                ),
                                value=total,
                            )
                        )
        return forecasts


def _section(payload: Any, name: str) -> dict[str, Any]:
    section = payload.get(name) if isinstance(payload, dict) else None
    if not isinstance(section, dict) or "time" not in section:
        raise SourceUnavailableError(f"Open-Meteo response has no '{name}' section")
    return section


def _strings(section: dict[str, Any], key: str) -> list[str]:
    values = section.get(key)
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise SourceUnavailableError(f"Open-Meteo response has no '{key}' list")
    return values


def _series(
    section: dict[str, Any], parameter: str, provider_name: str, model_count: int, length: int
) -> list[float | None]:
    """One model's values for one parameter.

    With several models Open-Meteo suffixes every key with the model name. With a
    single model it leaves the key bare.
    """
    keys = [f"{parameter}_{provider_name}"]
    if model_count == 1:
        keys.append(parameter)
    for key in keys:
        values = section.get(key)
        if values is None:
            continue
        if not isinstance(values, list) or len(values) != length:
            raise SourceUnavailableError(f"Open-Meteo series '{key}' has an unexpected shape")
        return [None if value is None else float(value) for value in values]
    return [None] * length
