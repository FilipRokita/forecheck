import math

from hypothesis import given
from hypothesis import strategies as st

from forecheck.domain.stats import ErrorStats
from tests.strategies import error_stats


@given(error_stats, error_stats, error_stats)
def test_addition_is_associative(a: ErrorStats, b: ErrorStats, c: ErrorStats) -> None:
    assert (a + b) + c == a + (b + c)


@given(error_stats, error_stats)
def test_addition_is_commutative(a: ErrorStats, b: ErrorStats) -> None:
    assert a + b == b + a


@given(error_stats)
def test_empty_stats_are_the_identity(a: ErrorStats) -> None:
    assert a + ErrorStats() == a == ErrorStats() + a


def test_nothing_scored_gives_no_figures() -> None:
    empty = ErrorStats()
    assert empty.mae is None
    assert empty.bias is None
    assert empty.rmse is None
    assert empty.accuracy is None
    assert empty.hit_rate is None
    assert empty.false_alarm_ratio is None
    assert empty.brier is None


def test_derived_figures() -> None:
    stats = ErrorStats(
        n=4,
        abs_error_sum=6.0,
        error_sum=-2.0,
        squared_error_sum=16.0,
        hits=3,
        misses=1,
        false_alarms=2,
        correct_negatives=4,
        brier_sum=1.0,
        brier_n=10,
    )
    assert stats.mae == 1.5
    assert stats.bias == -0.5
    assert stats.rmse == 2.0
    assert stats.event_days == 10
    assert stats.accuracy == 0.7
    assert stats.hit_rate == 0.75
    assert stats.false_alarm_ratio == 0.4
    assert stats.brier == 0.1


@given(st.lists(error_stats, min_size=1, max_size=8))
def test_the_mean_of_a_sum_is_the_weighted_mean(parts: list[ErrorStats]) -> None:
    total = ErrorStats()
    for part in parts:
        total += part
    if total.n:
        assert total.mae is not None
        assert math.isclose(total.mae, sum(p.abs_error_sum for p in parts) / total.n)
