"""Fetch today's forecasts for every station and keep them until their day is measured."""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from forecheck.application.catalog import Catalog
from forecheck.application.errors import RateLimitedError, SourceError
from forecheck.application.ports import Clock, ForecastSource, UnitOfWorkFactory
from forecheck.domain.types import StationId

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CollectionReport:
    stored: int
    failed: tuple[StationId, ...]
    rate_limited: bool

    @property
    def ok(self) -> bool:
        return not self.failed and not self.rate_limited


class CollectForecasts:
    def __init__(
        self,
        source: ForecastSource,
        uow_factory: UnitOfWorkFactory,
        clock: Clock,
        catalog: Catalog,
        pause: Callable[[], None] = lambda: None,
    ) -> None:
        self._source = source
        self._uow_factory = uow_factory
        self._clock = clock
        self._catalog = catalog
        self._pause = pause

    def run(self) -> CollectionReport:
        issued_at = self._clock.now()
        stored = 0
        failed: list[StationId] = []
        rate_limited = False

        for index, station in enumerate(self._catalog.stations):
            if index:
                self._pause()
            try:
                forecasts = self._source.fetch_forecasts(station, issued_at)
            except RateLimitedError:
                # The quota will not clear within this run: stop asking, tomorrow's run continues.
                log.warning("Forecast provider is rate limiting; stopping at %s", station.name)
                rate_limited = True
                failed.extend(s.id for s in self._catalog.stations[index:])
                break
            except SourceError as error:
                log.warning("No forecasts for %s: %s", station.name, error)
                failed.append(station.id)
                continue

            with self._uow_factory() as uow:
                uow.forecasts.upsert(forecasts)
                uow.commit()
            stored += len(forecasts)
        return CollectionReport(stored, tuple(failed), rate_limited)
