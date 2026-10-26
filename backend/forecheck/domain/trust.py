"""How many days ahead a forecast can be trusted."""

from collections.abc import Mapping

from forecheck.domain.rules import Rules
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import MAX_LEAD_DAYS, MIN_LEAD_DAYS, Variable


def passes(variable: Variable, stats: ErrorStats, rules: Rules) -> bool:
    """Whether a lead is good enough: error under the ceiling, or enough right calls."""
    threshold = rules.trust_thresholds[variable]
    if variable.is_event:
        accuracy = stats.accuracy
        return accuracy is not None and accuracy >= threshold
    mae = stats.mae
    return mae is not None and mae <= threshold


def trust_horizon(
    variable: Variable, per_lead: Mapping[int, ErrorStats], rules: Rules
) -> int | None:
    """Largest lead N such that every lead from 1 to N passes.

    Stops at the first lead that fails or lacks enough scored days, so a lucky
    day 5 behind a bad day 3 does not extend the horizon. Returns ``None`` when
    even day 1 cannot be judged, and 0 when day 1 fails.
    """
    first = per_lead.get(MIN_LEAD_DAYS)
    if first is None or first.n < rules.min_samples:
        return None

    horizon = 0
    for lead in range(MIN_LEAD_DAYS, MAX_LEAD_DAYS + 1):
        stats = per_lead.get(lead)
        if stats is None or stats.n < rules.min_samples or not passes(variable, stats, rules):
            break
        horizon = lead
    return horizon
