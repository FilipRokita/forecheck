"""Read the station measurements that forecasts are waiting for."""

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from forecheck.application.catalog import Catalog
from forecheck.application.ports import Clock, ObservationSource, UnitOfWorkFactory

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IngestReport:
    months_read: int
    observations: int


def _next_month(month: date) -> date:
    return (month + timedelta(days=32)).replace(day=1)


def _last_day(month: date) -> date:
    return _next_month(month) - timedelta(days=1)


class IngestObservations:
    """Fetches only months the provider has republished since the last read.

    A UTC day's precipitation needs the 00 UTC report of the day after, so the last day of
    a month is only complete once the next month's file exists. A month is therefore
    fingerprinted by its own version and the next month's, and read again when either changes.
    """

    def __init__(
        self,
        source: ObservationSource,
        uow_factory: UnitOfWorkFactory,
        clock: Clock,
        catalog: Catalog,
    ) -> None:
        self._source = source
        self._uow_factory = uow_factory
        self._clock = clock
        self._catalog = catalog

    def run(self) -> IngestReport:
        yesterday = self._clock.now().date() - timedelta(days=1)
        with self._uow_factory() as uow:
            earliest = uow.forecasts.earliest_valid_date()
        if earliest is None or earliest > yesterday:
            return IngestReport(0, 0)
        return self.read_range(earliest, yesterday)

    def read_range(self, start: date, end: date) -> IngestReport:
        """Read measurements for ``start``..``end``, skipping months that have not changed."""
        stations = self._catalog.stations
        versions = self._source.available_months(stations, start, end + timedelta(days=1))

        months_read = 0
        total = 0
        for month, version in sorted(versions.items()):
            if month > end:
                continue  # only here for the day-after report of the previous month
            fingerprint = f"{version}|{versions.get(_next_month(month), '-')}"
            key = f"observations:{month:%Y-%m}"
            with self._uow_factory() as uow:
                if uow.state.get(key) == fingerprint:
                    continue
            observations = self._source.fetch_observations(
                stations, max(start, month), min(end, _last_day(month))
            )
            with self._uow_factory() as uow:
                uow.observations.upsert(observations)
                uow.state.set(key, fingerprint)
                uow.commit()
            log.info("Read %s: %d observations", month, len(observations))
            months_read += 1
            total += len(observations)
        return IngestReport(months_read, total)
