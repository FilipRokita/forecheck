"""The tunable rules of the method, in one place."""

from dataclasses import dataclass, field

from forecheck.domain.types import Variable


def _default_trust_thresholds() -> dict[Variable, float]:
    return {
        Variable.TEMPERATURE: 2.0,  # mean absolute error, °C
        Variable.WIND: 1.5,  # mean absolute error, m/s
        Variable.PRESSURE: 2.0,  # mean absolute error, hPa
        Variable.PRECIPITATION: 0.8,  # share of days the yes/no call was right
    }


@dataclass(frozen=True, slots=True)
class Rules:
    """How forecasts are judged.

    ``trust_thresholds`` says how good a forecast must be at a given lead to be
    trusted: a ceiling on the mean absolute error for measured quantities, a
    floor on the share of correct calls for precipitation.
    """

    # A day counts as wet when at least this much fell, in mm.
    precipitation_threshold_mm: float = 0.1
    trust_thresholds: dict[Variable, float] = field(default_factory=_default_trust_thresholds)
    # Fewer scored days than this and a score is shown but not ranked or trusted.
    min_samples: int = 10
    # The headline ranking looks at leads 1 to this many days.
    ranking_lead_max: int = 3

    def __post_init__(self) -> None:
        if self.precipitation_threshold_mm <= 0:
            raise ValueError("precipitation_threshold_mm must be positive")
        if self.min_samples < 1:
            raise ValueError("min_samples must be at least 1")
        if not 1 <= self.ranking_lead_max <= 7:
            raise ValueError("ranking_lead_max must be 1 to 7")
        missing = set(Variable) - set(self.trust_thresholds)
        if missing:
            raise ValueError(f"trust_thresholds lacks {sorted(v.value for v in missing)}")
