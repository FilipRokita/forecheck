from hypothesis import given
from hypothesis import strategies as st

from forecheck.domain.rules import Rules
from forecheck.domain.stats import ErrorStats
from forecheck.domain.trust import trust_horizon
from forecheck.domain.types import MAX_LEAD_DAYS, Variable

RULES = Rules(min_samples=10)


def mae(value: float, n: int = 20) -> ErrorStats:
    return ErrorStats(n=n, abs_error_sum=value * n)


def test_the_horizon_is_the_last_lead_under_the_ceiling() -> None:
    per_lead = {1: mae(1.0), 2: mae(1.4), 3: mae(1.9), 4: mae(2.6), 5: mae(3.0)}
    assert trust_horizon(Variable.TEMPERATURE, per_lead, RULES) == 3


def test_the_ceiling_itself_still_passes() -> None:
    assert trust_horizon(Variable.TEMPERATURE, {1: mae(2.0)}, RULES) == 1


def test_a_lucky_late_lead_does_not_extend_the_horizon() -> None:
    per_lead = {1: mae(1.0), 2: mae(3.0), 3: mae(1.0)}
    assert trust_horizon(Variable.TEMPERATURE, per_lead, RULES) == 1


def test_a_forecast_that_fails_tomorrow_is_not_trusted_at_all() -> None:
    assert trust_horizon(Variable.TEMPERATURE, {1: mae(2.5)}, RULES) == 0


def test_without_enough_days_at_lead_one_the_horizon_is_unknown() -> None:
    assert trust_horizon(Variable.TEMPERATURE, {}, RULES) is None
    assert trust_horizon(Variable.TEMPERATURE, {1: mae(1.0, n=9)}, RULES) is None


def test_a_gap_in_the_data_ends_the_horizon() -> None:
    per_lead = {1: mae(1.0), 2: mae(1.0), 4: mae(1.0)}
    assert trust_horizon(Variable.TEMPERATURE, per_lead, RULES) == 2


def test_precipitation_needs_enough_right_calls() -> None:
    def calls(right: int, wrong: int) -> ErrorStats:
        return ErrorStats(n=right + wrong, hits=right, misses=wrong)

    per_lead = {1: calls(18, 2), 2: calls(16, 4), 3: calls(15, 5)}
    assert trust_horizon(Variable.PRECIPITATION, per_lead, RULES) == 2  # 90%, 80%, then 75%


@given(st.lists(st.floats(0, 6, allow_nan=False), min_size=1, max_size=MAX_LEAD_DAYS))
def test_every_lead_inside_the_horizon_passes_and_the_next_one_does_not(
    errors: list[float],
) -> None:
    per_lead = {lead: mae(value) for lead, value in enumerate(errors, start=1)}
    horizon = trust_horizon(Variable.TEMPERATURE, per_lead, RULES)
    assert horizon is not None
    assert all(errors[lead - 1] <= 2.0 for lead in range(1, horizon + 1))
    if horizon < len(errors):
        assert errors[horizon] > 2.0
