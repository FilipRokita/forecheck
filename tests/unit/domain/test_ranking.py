from hypothesis import given
from hypothesis import strategies as st

from forecheck.domain.ranking import rank_models
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import ModelId, Variable
from tests.strategies import error_stats

ICON, ECMWF, GFS = ModelId("icon"), ModelId("ecmwf"), ModelId("gfs")


def temperature(n: int, abs_error_sum: float) -> ErrorStats:
    return ErrorStats(n=n, abs_error_sum=abs_error_sum, squared_error_sum=abs_error_sum**2)


def test_the_lowest_error_ranks_first() -> None:
    ranked = rank_models(
        Variable.TEMPERATURE,
        {ICON: temperature(20, 28.0), ECMWF: temperature(20, 26.0), GFS: temperature(20, 36.0)},
        min_samples=10,
    )
    assert [(r.model, r.rank) for r in ranked] == [(ECMWF, 1), (ICON, 2), (GFS, 3)]


def test_models_with_too_few_days_are_listed_last_and_unranked() -> None:
    ranked = rank_models(
        Variable.TEMPERATURE,
        {ICON: temperature(3, 0.3), ECMWF: temperature(20, 26.0), GFS: temperature(20, 36.0)},
        min_samples=10,
    )
    assert [(r.model, r.rank) for r in ranked] == [(ECMWF, 1), (GFS, 2), (ICON, None)]


def test_precipitation_is_ranked_by_accuracy_then_brier() -> None:
    better = ErrorStats(n=10, hits=4, correct_negatives=5, misses=1, brier_sum=1.0, brier_n=10)
    worse = ErrorStats(
        n=10, hits=3, correct_negatives=5, misses=1, false_alarms=1, brier_sum=0.5, brier_n=10
    )
    tied_but_sharper = ErrorStats(
        n=10, hits=4, correct_negatives=5, misses=1, brier_sum=0.5, brier_n=10
    )
    ranked = rank_models(
        Variable.PRECIPITATION, {ICON: better, ECMWF: worse, GFS: tied_but_sharper}, min_samples=10
    )
    assert [r.model for r in ranked] == [GFS, ICON, ECMWF]


def test_ties_are_broken_by_name_so_the_order_is_stable() -> None:
    same = temperature(20, 20.0)
    ranked = rank_models(Variable.TEMPERATURE, {GFS: same, ICON: same, ECMWF: same}, min_samples=10)
    assert [r.model for r in ranked] == [ECMWF, GFS, ICON]


@given(st.dictionaries(st.sampled_from([ICON, ECMWF, GFS]), error_stats), st.integers(1, 50))
def test_ranks_are_consecutive_from_one_and_cover_every_model(
    scores: dict[ModelId, ErrorStats], min_samples: int
) -> None:
    for variable in Variable:
        ranked = rank_models(variable, scores, min_samples=min_samples)
        assert {r.model for r in ranked} == set(scores)
        ranks = [r.rank for r in ranked if r.rank is not None]
        assert ranks == list(range(1, len(ranks) + 1))
        assert all((r.rank is None) == (r.stats.n < min_samples) for r in ranked)
