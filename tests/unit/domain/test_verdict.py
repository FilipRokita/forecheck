import pytest

from forecheck.domain.rules import Rules
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import ModelId, Variable
from forecheck.domain.verdict import build_verdict, merge_leads

ICON, ECMWF, GFS = ModelId("icon"), ModelId("ecmwf"), ModelId("gfs")
RULES = Rules(min_samples=10)


def mae(value: float, n: int = 20) -> ErrorStats:
    return ErrorStats(n=n, abs_error_sum=value * n)


def test_only_the_leads_up_to_the_limit_are_merged() -> None:
    merged = merge_leads({1: mae(1.0, 10), 2: mae(2.0, 10), 4: mae(9.0, 10)}, up_to=3)
    assert merged.n == 20
    assert merged.mae == pytest.approx(1.5)


def test_the_verdict_names_the_best_model_and_how_far_to_trust_it() -> None:
    stats = {
        ECMWF: {1: mae(1.0), 2: mae(1.5), 3: mae(1.8), 4: mae(2.6)},
        ICON: {1: mae(1.2), 2: mae(1.6), 3: mae(2.1), 4: mae(2.4)},
        GFS: {1: mae(1.8), 2: mae(2.2), 3: mae(2.8), 4: mae(3.5)},
    }
    verdict = build_verdict(Variable.TEMPERATURE, stats, RULES)
    assert verdict.best == ECMWF
    assert [r.model for r in verdict.ranking] == [ECMWF, ICON, GFS]
    assert verdict.trust_days == 3
    assert verdict.next_day == stats[ECMWF][1]


def test_without_enough_data_there_is_no_best_model() -> None:
    verdict = build_verdict(Variable.TEMPERATURE, {ECMWF: {1: mae(1.0, n=3)}}, RULES)
    assert verdict.best is None
    assert verdict.trust_days is None
    assert verdict.next_day is None
    assert [(r.model, r.rank) for r in verdict.ranking] == [(ECMWF, None)]


def test_no_models_at_all_is_not_an_error() -> None:
    verdict = build_verdict(Variable.TEMPERATURE, {}, RULES)
    assert verdict.ranking == []
    assert verdict.best is None


def test_rules_reject_nonsense() -> None:
    with pytest.raises(ValueError, match="positive"):
        Rules(precipitation_threshold_mm=0)
    with pytest.raises(ValueError, match="min_samples"):
        Rules(min_samples=0)
    with pytest.raises(ValueError, match="ranking_lead_max"):
        Rules(ranking_lead_max=8)
    with pytest.raises(ValueError, match="trust_thresholds"):
        Rules(trust_thresholds={Variable.TEMPERATURE: 2.0})
