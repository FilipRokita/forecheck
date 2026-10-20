"""Error statistics that can be added together.

A day's scores are stored as one ``ErrorStats`` per station, model, variable and
lead. A ranking over any period is the sum of those rows, so raw forecasts do not
have to be kept once they are scored. Addition is associative and commutative,
with ``ErrorStats()`` as the identity, which the tests check as properties.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ErrorStats:
    """Sums over scored days. Means and rates are derived, never stored."""

    n: int = 0
    abs_error_sum: float = 0.0
    error_sum: float = 0.0  # signed, forecast minus observed: the bias
    squared_error_sum: float = 0.0
    # Precipitation as a yes/no call.
    hits: int = 0
    misses: int = 0
    false_alarms: int = 0
    correct_negatives: int = 0
    # Brier score, over the days where the provider gave a probability.
    brier_sum: float = 0.0
    brier_n: int = 0

    def __add__(self, other: "ErrorStats") -> "ErrorStats":
        return ErrorStats(
            n=self.n + other.n,
            abs_error_sum=self.abs_error_sum + other.abs_error_sum,
            error_sum=self.error_sum + other.error_sum,
            squared_error_sum=self.squared_error_sum + other.squared_error_sum,
            hits=self.hits + other.hits,
            misses=self.misses + other.misses,
            false_alarms=self.false_alarms + other.false_alarms,
            correct_negatives=self.correct_negatives + other.correct_negatives,
            brier_sum=self.brier_sum + other.brier_sum,
            brier_n=self.brier_n + other.brier_n,
        )

    @property
    def mae(self) -> float | None:
        """Mean absolute error, in the unit of the variable."""
        return self.abs_error_sum / self.n if self.n else None

    @property
    def bias(self) -> float | None:
        """Mean signed error: positive when the model runs high."""
        return self.error_sum / self.n if self.n else None

    @property
    def rmse(self) -> float | None:
        return math.sqrt(self.squared_error_sum / self.n) if self.n else None

    @property
    def event_days(self) -> int:
        return self.hits + self.misses + self.false_alarms + self.correct_negatives

    @property
    def accuracy(self) -> float | None:
        """Share of days the wet/dry call was right."""
        total = self.event_days
        return (self.hits + self.correct_negatives) / total if total else None

    @property
    def hit_rate(self) -> float | None:
        """Share of wet days the model called wet (probability of detection)."""
        wet = self.hits + self.misses
        return self.hits / wet if wet else None

    @property
    def false_alarm_ratio(self) -> float | None:
        """Share of wet calls that turned out dry."""
        called = self.hits + self.false_alarms
        return self.false_alarms / called if called else None

    @property
    def brier(self) -> float | None:
        """Mean squared gap between the stated chance and what happened. Lower is better."""
        return self.brier_sum / self.brier_n if self.brier_n else None
