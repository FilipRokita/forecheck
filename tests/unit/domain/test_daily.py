import pytest
from hypothesis import given
from hypothesis import strategies as st

from forecheck.domain.daily import MIN_HOURLY_REPORTS, daily_mean, daily_precipitation


def test_a_complete_day_has_a_mean() -> None:
    assert daily_mean([float(h) for h in range(24)]) == 11.5


def test_a_few_missing_hours_are_tolerated() -> None:
    hourly: list[float | None] = [10.0] * 24
    for hour in range(24 - MIN_HOURLY_REPORTS):
        hourly[hour] = None
    assert daily_mean(hourly) == 10.0


def test_too_many_missing_hours_leave_the_day_unknown() -> None:
    hourly: list[float | None] = [10.0] * (MIN_HOURLY_REPORTS - 1) + [None] * (
        25 - MIN_HOURLY_REPORTS
    )
    assert daily_mean(hourly) is None


@given(st.lists(st.floats(-50, 50, allow_nan=False), min_size=20, max_size=24))
def test_the_mean_lies_between_the_extremes(values: list[float]) -> None:
    mean = daily_mean(list(values))
    assert mean is not None
    assert min(values) - 1e-9 <= mean <= max(values) + 1e-9


def test_precipitation_adds_the_four_six_hour_totals() -> None:
    assert daily_precipitation({6: 0.0, 12: 1.5, 18: 0.2, 24: 0.3}) == pytest.approx(2.0)


@pytest.mark.parametrize("missing", [6, 12, 18, 24])
def test_a_missing_total_never_yields_a_partial_sum(missing: int) -> None:
    totals: dict[int, float | None] = {6: 1.0, 12: 1.0, 18: 1.0, 24: 1.0}
    totals[missing] = None
    assert daily_precipitation(totals) is None
    del totals[missing]
    assert daily_precipitation(totals) is None
