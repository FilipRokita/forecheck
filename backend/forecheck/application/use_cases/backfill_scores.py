"""Start with a history: score the forecasts the provider archived against the measurements."""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from forecheck.application.catalog import Catalog
from forecheck.application.ports import ForecastArchive, UnitOfWorkFactory
from forecheck.application.use_cases.ingest_observations import IngestObservations
from forecheck.domain.entities import ScoreRecord
from forecheck.domain.rules import Rules
from forecheck.domain.scoring import score
from forecheck.domain.types import StationId

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BackfillReport:
    observations: int
    scored: int


class BackfillScores:
    """Idempotent: a score is keyed by station, variable, day, model and lead, so runs can repeat.

    A score that already exists is kept. One made from a forecast fetched on the day is what the
    method promises, and it has a Brier score, which the archive's reconstruction (stamped at
    00 UTC, with no chance of rain) cannot match.
    """

    def __init__(
        self,
        archive: ForecastArchive,
        ingest: IngestObservations,
        uow_factory: UnitOfWorkFactory,
        catalog: Catalog,
        rules: Rules,
        pause: Callable[[], None] = lambda: None,
    ) -> None:
        self._archive = archive
        self._ingest = ingest
        self._uow_factory = uow_factory
        self._catalog = catalog
        self._rules = rules
        self._pause = pause

    def run(
        self, start: date, end: date, only: Sequence[StationId] | None = None
    ) -> BackfillReport:
        ingested = self._ingest.read_range(start, end)

        stations = [s for s in self._catalog.stations if only is None or s.id in only]
        with self._uow_factory() as uow:
            observed = {
                (o.station_id, o.variable, o.day): o for o in uow.observations.between(start, end)
            }

        total = 0
        for index, station in enumerate(stations):
            if index:
                self._pause()
            records = []
            for forecast in self._archive.fetch_archived_forecasts(station, start, end):
                observation = observed.get(
                    (forecast.station_id, forecast.variable, forecast.valid_date)
                )
                if observation is None:
                    continue
                records.append(
                    ScoreRecord(
                        station_id=forecast.station_id,
                        model=forecast.model,
                        variable=forecast.variable,
                        lead_days=forecast.lead_days,
                        valid_date=forecast.valid_date,
                        stats=score(forecast, observation, self._rules),
                    )
                )
            with self._uow_factory() as uow:
                inserted = uow.scores.insert_missing(records)
                uow.commit()
            log.info("Backfilled %s: %d new scores", station.name, inserted)
            total += inserted
        return BackfillReport(observations=ingested.observations, scored=total)
