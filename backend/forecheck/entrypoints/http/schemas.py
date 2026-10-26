"""The JSON the API speaks. These models are the contract: the OpenAPI document, and from it
``src/lib/api/schema.ts``, are generated from them."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Metric = Literal["mae", "accuracy"]


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StationOut(Schema):
    id: str
    name: str
    latitude: float
    longitude: float


class ModelOut(Schema):
    id: str
    label: str


class VariableOut(Schema):
    id: str
    label: str
    unit: str
    # What the figures are judged on: mean absolute error, or the share of right wet/dry calls.
    metric: Metric
    # The ceiling (mae) or floor (accuracy) a lead must meet to be trusted.
    trust_threshold: float


class PeriodOut(Schema):
    id: str
    label: str
    days: int


class AttributionOut(Schema):
    open_meteo: str
    open_meteo_url: str
    open_meteo_licence: str
    imgw_source: str
    imgw_processed: str
    imgw_url: str


class RunOut(Schema):
    kind: str
    at: datetime
    ok: bool
    message: str


class StatusOut(Schema):
    sample_data: bool = Field(description="True while the scores are made-up demo data.")
    latest_scored_day: date | None
    waiting_forecasts: int
    last_runs: list[RunOut]


class MetaOut(Schema):
    stations: list[StationOut]
    models: list[ModelOut]
    variables: list[VariableOut]
    periods: list[PeriodOut]
    min_samples: int
    precipitation_threshold_mm: float
    ranking_lead_max: int
    attribution: AttributionOut
    status: StatusOut


class WindowOut(Schema):
    start: date
    end: date


class FigureOut(Schema):
    """Every figure for one model over some scored days. A figure that does not apply is null."""

    n: int = Field(description="Scored days.")
    mae: float | None
    bias: float | None
    rmse: float | None
    accuracy: float | None = Field(
        description="Share of days the wet/dry call was right (precipitation)."
    )
    hit_rate: float | None
    false_alarm_ratio: float | None
    brier: float | None


class RankedModelOut(FigureOut):
    model: str
    label: str
    # 1 is best. Null when there are too few scored days to rank the model.
    rank: int | None


class VerdictOut(Schema):
    station: StationOut
    variable: str
    period: str
    window: WindowOut | None
    lead_from: int
    lead_to: int
    best_model: str | None
    best_model_label: str | None
    # Days ahead the best model can be trusted. Null while that cannot be judged yet.
    trust_days: int | None
    next_day: FigureOut | None = Field(description="The best model's day-ahead figures.")
    scored_days: int
    ranking: list[RankedModelOut]


class LeadFigureOut(FigureOut):
    lead_days: int


class ModelHorizonOut(Schema):
    model: str
    label: str
    leads: list[LeadFigureOut]


class HorizonOut(Schema):
    station: StationOut
    variable: str
    period: str
    window: WindowOut | None
    metric: Metric
    trust_threshold: float
    models: list[ModelHorizonOut]


class ComparisonRowOut(Schema):
    station: StationOut
    best_model: str | None
    best_model_label: str | None
    figures: FigureOut | None


class ComparisonOut(Schema):
    variable: str
    period: str
    lead_days: int
    window: WindowOut | None
    metric: Metric
    rows: list[ComparisonRowOut]


class CycleStepOut(Schema):
    name: str
    ok: bool
    message: str


class CycleOut(Schema):
    ok: bool
    steps: list[CycleStepOut]


class HealthOut(Schema):
    status: Literal["ok"]
