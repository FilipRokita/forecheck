"""The records the domain reasons about."""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from forecheck.domain.types import MAX_LEAD_DAYS, MIN_LEAD_DAYS, ModelId, StationId, Variable


@dataclass(frozen=True, slots=True)
class Station:
    """An IMGW synoptic station: the place a forecast is checked at."""

    id: StationId
    name: str
    latitude: float
    longitude: float


def lead_days(issued_at: datetime, valid_date: date) -> int:
    """Whole days between the UTC day a forecast was issued and the day it is about."""
    if issued_at.tzinfo is None:
        raise ValueError("issued_at must be timezone-aware")
    return (valid_date - issued_at.astimezone(UTC).date()).days


@dataclass(frozen=True, slots=True)
class Forecast:
    """One model's forecast of one daily figure, as it was issued ahead of time.

    ``issued_at`` is when the forecast was fetched, not when it was refreshed:
    a forecast corrected shortly before its day would make every model look better
    than it was when someone could still act on it.
    """

    station_id: StationId
    model: ModelId
    variable: Variable
    valid_date: date
    issued_at: datetime
    value: float
    # Chance of precipitation, 0 to 1, when the provider gives one. Only used for the Brier score.
    probability: float | None = None

    def __post_init__(self) -> None:
        lead = lead_days(self.issued_at, self.valid_date)
        if not MIN_LEAD_DAYS <= lead <= MAX_LEAD_DAYS:
            raise ValueError(f"lead must be {MIN_LEAD_DAYS} to {MAX_LEAD_DAYS} days, got {lead}")
        if self.probability is not None and not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability must be between 0 and 1")

    @property
    def lead_days(self) -> int:
        return lead_days(self.issued_at, self.valid_date)


@dataclass(frozen=True, slots=True)
class Observation:
    """What a station measured over one UTC day. This is the ground truth."""

    station_id: StationId
    variable: Variable
    day: date
    value: float
