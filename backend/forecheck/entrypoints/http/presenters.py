"""Turning application results into API schemas."""

from collections.abc import Mapping

from forecheck.application.catalog import Catalog
from forecheck.application.queries import ExportRow, Window
from forecheck.domain.entities import Station
from forecheck.domain.rules import Rules
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import ModelId, Period, Variable
from forecheck.entrypoints.http import schemas

VARIABLE_LABELS: Mapping[Variable, str] = {
    Variable.TEMPERATURE: "Temperature",
    Variable.PRECIPITATION: "Precipitation",
    Variable.WIND: "Wind",
    Variable.PRESSURE: "Pressure",
}
PERIOD_LABELS: Mapping[Period, str] = {
    Period.DAYS_30: "30 days",
    Period.DAYS_90: "90 days",
    Period.MONTHS_12: "12 months",
}


def metric_of(variable: Variable) -> schemas.Metric:
    return "accuracy" if variable.is_event else "mae"


def station_out(station: Station) -> schemas.StationOut:
    return schemas.StationOut(
        id=station.id, name=station.name, latitude=station.latitude, longitude=station.longitude
    )


def window_out(window: Window | None) -> schemas.WindowOut | None:
    return None if window is None else schemas.WindowOut(start=window.start, end=window.end)


def figures(stats: ErrorStats) -> dict[str, float | int | None]:
    return {
        "n": stats.n,
        "mae": stats.mae,
        "bias": stats.bias,
        "rmse": stats.rmse,
        "accuracy": stats.accuracy,
        "hit_rate": stats.hit_rate,
        "false_alarm_ratio": stats.false_alarm_ratio,
        "brier": stats.brier,
    }


def figure_out(stats: ErrorStats) -> schemas.FigureOut:
    return schemas.FigureOut.model_validate(figures(stats))


def model_label(catalog: Catalog, model: ModelId) -> str:
    spec = catalog.model(model)
    return spec.label if spec else model


def variable_out(variable: Variable, rules: Rules) -> schemas.VariableOut:
    return schemas.VariableOut(
        id=variable.value,
        label=VARIABLE_LABELS[variable],
        unit=variable.unit,
        metric=metric_of(variable),
        trust_threshold=rules.trust_thresholds[variable],
    )


def export_header() -> list[str]:
    return [
        "station_id",
        "station",
        "variable",
        "unit",
        "period",
        "model",
        "lead_days",
        "scored_days",
        "mae",
        "bias",
        "rmse",
        "accuracy",
        "hit_rate",
        "false_alarm_ratio",
        "brier",
    ]


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def export_row(
    station: Station, variable: Variable, period: Period, row: ExportRow
) -> list[str | int | float | None]:
    stats = row.stats
    return [
        station.id,
        station.name,
        variable.value,
        variable.unit,
        period.value,
        row.model,
        row.lead_days,
        stats.n,
        _rounded(stats.mae),
        _rounded(stats.bias),
        _rounded(stats.rmse),
        _rounded(stats.accuracy),
        _rounded(stats.hit_rate),
        _rounded(stats.false_alarm_ratio),
        _rounded(stats.brier),
    ]
