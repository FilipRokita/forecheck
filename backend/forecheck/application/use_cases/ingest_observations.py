"""Read the station measurements that forecasts are waiting for."""

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from forecheck.application.catalog import Catalog
from forecheck.application.errors import SourceError
from forecheck.application.ports import Clock, ObservationSource, UnitOfWorkFactory

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IngestReport:
    months_read: int
    observations: int
    # Months that could not be read. They are tried again on the next run.
    failed: tuple[date, ...] = ()


FINGERPRINT_PREFIX = "observations:"


def fingerprint_key(month: date) -> str:
    """The key under which what was read of ``month`` is remembered. Sorts by month."""
    return f"{FINGERPRINT_PREFIX}{month:%Y-%m}"


def next_month(day: date) -> date:
    """The first day of the month after the one ``day`` is in."""
    return (day.replace(day=1) + timedelta(days=32)).replace(day=1)


def _last_day(month: date) -> date:
    return next_month(month) - timedelta(days=1)


def _covers(stored: str | None, versioned: str, first: date, last: date) -> bool:
    """Whether a stored fingerprint is for the same versions and for days including first..last."""
    if stored is None:
        return False
    parts = stored.rsplit("|", 2)
    if len(parts) != 3 or parts[0] != versioned:  # also true of a fingerprint without days
        return False
    return date.fromisoformat(parts[1]) <= first and last <= date.fromisoformat(parts[2])


class IngestObservations:
    """Fetches only months the provider has republished since the last read.

    A UTC day's precipitation needs the 00 UTC report of the day after, so the last day of
    a month is only complete once the next month's file exists. A month is therefore
    fingerprinted by its own version and the next month's, and read again when either changes.

    A read may cover only part of a month (a range starting mid-month). The days it covered are
    kept with the fingerprint, so a later read of other days of the same month is not skipped.
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
        failed: list[date] = []
        for month, version in sorted(versions.items()):
            if month > end:
                continue  # only here for the day-after report of the previous month
            versioned = f"{version}|{versions.get(next_month(month), '-')}"
            key = fingerprint_key(month)
            first, last = max(start, month), min(end, _last_day(month))
            with self._uow_factory() as uow:
                if _covers(uow.state.get(key), versioned, first, last):
                    continue
            try:
                observations = self._source.fetch_observations(stations, first, last)
            except SourceError as error:
                # One unreadable month must not hold back the newer ones that are published.
                log.warning("Could not read %s: %s", month, error)
                failed.append(month)
                continue
            with self._uow_factory() as uow:
                uow.observations.upsert(observations)
                uow.state.set(key, f"{versioned}|{first.isoformat()}|{last.isoformat()}")
                uow.commit()
            log.info("Read %s: %d observations", month, len(observations))
            months_read += 1
            total += len(observations)
        return IngestReport(months_read, total, tuple(failed))
