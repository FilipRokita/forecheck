"""The answer a visitor gets first: which model to trust here, and for how long."""

from collections.abc import Mapping
from dataclasses import dataclass

from forecheck.domain.ranking import RankedModel, rank_models
from forecheck.domain.rules import Rules
from forecheck.domain.stats import ErrorStats
from forecheck.domain.trust import trust_horizon
from forecheck.domain.types import MIN_LEAD_DAYS, ModelId, Variable


@dataclass(frozen=True, slots=True)
class Verdict:
    variable: Variable
    # Models over leads 1 to ``Rules.ranking_lead_max``, best first.
    ranking: list[RankedModel]
    best: ModelId | None
    # Days ahead the best model can be trusted. ``None`` when it cannot be judged yet.
    trust_days: int | None
    # The best model's day-1 stats, for "how often tomorrow's call is right".
    next_day: ErrorStats | None


def merge_leads(per_lead: Mapping[int, ErrorStats], *, up_to: int) -> ErrorStats:
    """Add the stats of leads 1 to ``up_to``."""
    total = ErrorStats()
    for lead, stats in per_lead.items():
        if MIN_LEAD_DAYS <= lead <= up_to:
            total += stats
    return total


def build_verdict(
    variable: Variable, stats: Mapping[ModelId, Mapping[int, ErrorStats]], rules: Rules
) -> Verdict:
    """Rank the models on the short range and read the best one's trust horizon."""
    headline = {
        model: merge_leads(per_lead, up_to=rules.ranking_lead_max)
        for model, per_lead in stats.items()
    }
    ranking = rank_models(variable, headline, min_samples=rules.min_samples)

    best = ranking[0].model if ranking and ranking[0].rank == 1 else None
    if best is None:
        return Verdict(variable, ranking, None, None, None)
    return Verdict(
        variable=variable,
        ranking=ranking,
        best=best,
        trust_days=trust_horizon(variable, stats[best], rules),
        next_day=stats[best].get(MIN_LEAD_DAYS),
    )
