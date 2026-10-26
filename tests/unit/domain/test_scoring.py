from datetime import UTC, date, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from forecheck.domain.entities import Forecast, Observation
from forecheck.domain.rules import Rules
from forecheck.domain.scoring import score
from forecheck.domain.types import ModelId, StationId, Variable
from tests.strategies import forecasts, observation_for, values

RULES = Rules()
STATION = StationId("12566")
DAY = date(2026, 9, 10)


def make(variable: Variable, value: float, *, probability: float | None = None) -> Forecast:
    return Forecast(
        STATION,
        ModelId("ecmwf"),
        variable,
        DAY,
        datetime(2026, 9, 8, 9, 30, tzinfo=UTC),
        value,
        probability,
    )


def observed(variable: Variable, value: float) -> Observation:
    return Observation(STATION, variable, DAY, value)


def test_a_measured_error_is_signed_and_absolute() -> None:
    stats = score(make(Variable.TEMPERATURE, 12.0), observed(Variable.TEMPERATURE, 15.0), RULES)
    assert (stats.n, stats.abs_error_sum, stats.error_sum, stats.squared_error_sum) == (
        1,
        3.0,
        -3.0,
        9.0,
    )
    assert stats.event_days == 0
    assert stats.brier_n == 0


@pytest.mark.parametrize(
    ("forecast_mm", "observed_mm", "expected"),
    [
        (2.0, 1.0, "hits"),
        (0.0, 1.0, "misses"),
        (2.0, 0.0, "false_alarms"),
        (0.0, 0.0, "correct_negatives"),
        (0.1, 0.1, "hits"),  # the threshold itself counts as wet
        (0.09, 0.09, "correct_negatives"),
    ],
)
def test_precipitation_is_a_yes_no_call(
    forecast_mm: float, observed_mm: float, expected: str
) -> None:
    stats = score(
        make(Variable.PRECIPITATION, forecast_mm),
        observed(Variable.PRECIPITATION, observed_mm),
        RULES,
    )
    cells = {
        name: getattr(stats, name)
        for name in ("hits", "misses", "false_alarms", "correct_negatives")
    }
    assert cells == {name: int(name == expected) for name in cells}


def test_the_wet_threshold_comes_from_the_rules() -> None:
    strict = Rules(precipitation_threshold_mm=1.0)
    stats = score(make(Variable.PRECIPITATION, 0.5), observed(Variable.PRECIPITATION, 0.5), strict)
    assert stats.correct_negatives == 1


def test_brier_compares_the_stated_chance_with_what_happened() -> None:
    wet = score(
        make(Variable.PRECIPITATION, 2.0, probability=0.8),
        observed(Variable.PRECIPITATION, 3.0),
        RULES,
    )
    dry = score(
        make(Variable.PRECIPITATION, 2.0, probability=0.8),
        observed(Variable.PRECIPITATION, 0.0),
        RULES,
    )
    assert wet.brier == pytest.approx(0.04)
    assert dry.brier == pytest.approx(0.64)


def test_without_a_probability_there_is_no_brier() -> None:
    stats = score(make(Variable.PRECIPITATION, 2.0), observed(Variable.PRECIPITATION, 3.0), RULES)
    assert stats.brier is None


def test_a_forecast_is_only_scored_against_its_own_measurement() -> None:
    with pytest.raises(ValueError, match="different"):
        score(make(Variable.TEMPERATURE, 1.0), observed(Variable.WIND, 1.0), RULES)


@given(forecasts(), values)
def test_every_scored_day_is_one_sample(forecast: Forecast, observed_value: float) -> None:
    stats = score(forecast, observation_for(forecast, observed_value), RULES)
    assert stats.n == 1
    assert stats.abs_error_sum >= 0
    assert (
        stats.squared_error_sum >= stats.abs_error_sum**2 * 0.999999 or stats.squared_error_sum == 0
    )
    if forecast.variable is Variable.PRECIPITATION:
        assert stats.event_days == 1
        assert (stats.brier_n == 1) == (forecast.probability is not None)
    else:
        assert stats.event_days == 0


@given(forecasts(Variable.PRECIPITATION), st.floats(0, 200, allow_nan=False))
def test_the_brier_score_of_a_single_day_is_between_zero_and_one(
    forecast: Forecast, observed_mm: float
) -> None:
    stats = score(forecast, observation_for(forecast, observed_mm), RULES)
    if stats.brier is not None:
        assert 0.0 <= stats.brier <= 1.0
