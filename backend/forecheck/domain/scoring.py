"""Scoring one forecast against one measurement."""

from forecheck.domain.entities import Forecast, Observation
from forecheck.domain.rules import Rules
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import Variable


def score(forecast: Forecast, observation: Observation, rules: Rules) -> ErrorStats:
    """Turn a forecast and the measurement it is about into one day of statistics."""
    if (forecast.station_id, forecast.variable, forecast.valid_date) != (
        observation.station_id,
        observation.variable,
        observation.day,
    ):
        raise ValueError("forecast and observation are about different things")

    error = forecast.value - observation.value
    stats = ErrorStats(
        n=1, abs_error_sum=abs(error), error_sum=error, squared_error_sum=error * error
    )
    if forecast.variable is not Variable.PRECIPITATION:
        return stats

    threshold = rules.precipitation_threshold_mm
    predicted_wet = forecast.value >= threshold
    observed_wet = observation.value >= threshold
    stats += ErrorStats(
        hits=int(predicted_wet and observed_wet),
        misses=int(not predicted_wet and observed_wet),
        false_alarms=int(predicted_wet and not observed_wet),
        correct_negatives=int(not predicted_wet and not observed_wet),
    )
    if forecast.probability is not None:
        gap = forecast.probability - float(observed_wet)
        stats += ErrorStats(brier_sum=gap * gap, brier_n=1)
    return stats
