"""The vocabulary shared by the whole domain."""

from enum import StrEnum
from typing import NewType

StationId = NewType("StationId", str)
ModelId = NewType("ModelId", str)

# Lead time, in whole days, between the day a forecast was issued and the day it is about.
# Lead 0 is excluded: a forecast issued on the day it covers is partly an observation.
MIN_LEAD_DAYS = 1
MAX_LEAD_DAYS = 7


class Variable(StrEnum):
    """What is forecast and measured. Every value is a daily (UTC day) figure."""

    TEMPERATURE = "temperature"  # daily mean, °C
    PRECIPITATION = "precipitation"  # daily sum, mm
    WIND = "wind"  # daily mean speed, m/s
    PRESSURE = "pressure"  # daily mean, sea-level, hPa

    @property
    def unit(self) -> str:
        return _UNITS[self]

    @property
    def is_event(self) -> bool:
        """Whether the headline question is "did it happen?" (yes/no) rather than "by how much?"."""
        return self is Variable.PRECIPITATION


_UNITS: dict[Variable, str] = {
    Variable.TEMPERATURE: "°C",
    Variable.PRECIPITATION: "mm",
    Variable.WIND: "m/s",
    Variable.PRESSURE: "hPa",
}


class Period(StrEnum):
    """How far back a ranking looks, counted from the latest scored day."""

    DAYS_30 = "30d"
    DAYS_90 = "90d"
    MONTHS_12 = "12m"

    @property
    def days(self) -> int:
        return _PERIOD_DAYS[self]


_PERIOD_DAYS: dict[Period, int] = {
    Period.DAYS_30: 30,
    Period.DAYS_90: 90,
    Period.MONTHS_12: 365,
}
