"""Score the forecasts whose day has been measured, then drop them."""

from dataclasses import dataclass
from datetime import date, timedelta

from forecheck.application.ports import Clock, UnitOfWorkFactory
from forecheck.domain.entities import Forecast, Observation, ScoreRecord
from forecheck.domain.rules import Rules
from forecheck.domain.scoring import score
from forecheck.domain.types import StationId, Variable

# A forecast still unmatched this long after its day will never be: the measurement was
# incomplete. It is dropped so waiting forecasts cannot pile up.
DEFAULT_MAX_PENDING_DAYS = 90

# Scores older than this, counted back from the latest scored day, are dropped. The page reads at
# most 365 days (the 12 months period), so the rest is never shown. Two years leaves room for a
# longer view and stops the table from growing without end (about 90 MB a year).
DEFAULT_SCORE_RETENTION_DAYS = 730


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    scored: int
    expired: int
    pruned: int
    waiting: int


class EvaluateForecasts:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        clock: Clock,
        rules: Rules,
        max_pending_days: int = DEFAULT_MAX_PENDING_DAYS,
        score_retention_days: int = DEFAULT_SCORE_RETENTION_DAYS,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._rules = rules
        self._max_pending_days = max_pending_days
        self._score_retention_days = score_retention_days

    def run(self) -> EvaluationReport:
        with self._uow_factory() as uow:
            latest = uow.observations.latest_day()
            pending = uow.forecasts.pending(latest) if latest else []
            observed: dict[tuple[StationId, Variable, date], Observation] = {}
            if pending:
                first, last = pending[0].valid_date, pending[-1].valid_date
                observed = {
                    (o.station_id, o.variable, o.day): o
                    for o in uow.observations.between(first, last)
                }

            scored: list[ScoreRecord] = []
            matched: list[Forecast] = []
            for forecast in pending:
                observation = observed.get(
                    (forecast.station_id, forecast.variable, forecast.valid_date)
                )
                if observation is None:
                    continue
                scored.append(
                    ScoreRecord(
                        station_id=forecast.station_id,
                        model=forecast.model,
                        variable=forecast.variable,
                        lead_days=forecast.lead_days,
                        valid_date=forecast.valid_date,
                        stats=score(forecast, observation, self._rules),
                    )
                )
                matched.append(forecast)

            uow.scores.upsert(scored)
            uow.forecasts.delete(matched)
            expired = uow.forecasts.delete_valid_before(
                self._clock.now().date() - timedelta(days=self._max_pending_days)
            )
            latest_scored = uow.scores.latest_day()
            pruned = (
                uow.scores.delete_valid_before(
                    latest_scored - timedelta(days=self._score_retention_days)
                )
                if latest_scored
                else 0
            )
            waiting = uow.forecasts.count()
            uow.commit()
        return EvaluationReport(scored=len(scored), expired=expired, pruned=pruned, waiting=waiting)
