"""Ordering models against each other."""

from collections.abc import Mapping
from dataclasses import dataclass

from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import ModelId, Variable


@dataclass(frozen=True, slots=True)
class RankedModel:
    model: ModelId
    stats: ErrorStats
    # 1 for the best. ``None`` when there are too few scored days to rank the model.
    rank: int | None


def _sort_key(variable: Variable, stats: ErrorStats) -> tuple[float, float, float]:
    """Smaller sorts first. Ties fall through to the next measure, then to the model name."""
    mae = stats.mae if stats.mae is not None else float("inf")
    if variable.is_event:
        accuracy = stats.accuracy if stats.accuracy is not None else -1.0
        brier = stats.brier if stats.brier is not None else float("inf")
        return (-accuracy, brier, mae)
    return (mae, stats.rmse if stats.rmse is not None else float("inf"), 0.0)


def rank_models(
    variable: Variable,
    scores: Mapping[ModelId, ErrorStats],
    *,
    min_samples: int,
    scored_days: Mapping[ModelId, int] | None = None,
) -> list[RankedModel]:
    """Rank models best first. Models with too few scored days follow, unranked.

    ``scored_days`` is how many days each model's figures rest on. ``ErrorStats.n`` counts
    forecasts, so stats summed over several leads hold several per day. Without it, ``n`` is used.
    """

    def days(model: ModelId) -> int:
        return scores[model].n if scored_days is None else scored_days.get(model, 0)

    sufficient = {model: stats for model, stats in scores.items() if days(model) >= min_samples}
    insufficient = {model: stats for model, stats in scores.items() if days(model) < min_samples}

    ordered = sorted(sufficient.items(), key=lambda item: (_sort_key(variable, item[1]), item[0]))
    ranked = [
        RankedModel(model, stats, position)
        for position, (model, stats) in enumerate(ordered, start=1)
    ]
    unranked = [RankedModel(model, stats, None) for model, stats in sorted(insufficient.items())]
    return ranked + unranked
