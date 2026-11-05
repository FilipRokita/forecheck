"""Drop what the page can no longer show, so the database stops growing."""

from dataclasses import dataclass
from datetime import timedelta

from forecheck.application.ports import Clock, UnitOfWorkFactory
from forecheck.application.use_cases.ingest_observations import (
    FINGERPRINT_PREFIX,
    fingerprint_key,
    next_month,
)

# The page reads at most 365 days (the 12 months period). Two years leaves room for a longer view.
DEFAULT_RETENTION_DAYS = 730


@dataclass(frozen=True, slots=True)
class PruneReport:
    scores: int
    observations: int
    runs: int


class PruneOldData:
    """Keeps ``retention_days`` of scores, measurements and the run log.

    Scores and measurements are counted back from their own latest day, as the page counts its
    windows, so a run that stalls for a long time cannot delete what is still shown. The run log is
    counted back from now.

    Dropping measurements also drops what was remembered about reading their months. Otherwise a
    later backfill would believe those months are already in and score nothing.
    """

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        clock: Clock,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._retention = timedelta(days=retention_days)

    def run(self) -> PruneReport:
        with self._uow_factory() as uow:
            latest_score = uow.scores.latest_day()
            scores = (
                uow.scores.delete_valid_before(latest_score - self._retention)
                if latest_score
                else 0
            )

            observations = 0
            latest_observation = uow.observations.latest_day()
            if latest_observation:
                cutoff = latest_observation - self._retention
                observations = uow.observations.delete_before(cutoff)
                # The month of the cutoff day is now only partly there, so it goes too.
                uow.state.delete_before(FINGERPRINT_PREFIX, fingerprint_key(next_month(cutoff)))

            runs = uow.runs.delete_before(self._clock.now() - self._retention)
            uow.commit()
        return PruneReport(scores, observations, runs)
