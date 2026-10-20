"""What the use cases need from the outside world. Adapters implement these."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from types import TracebackType
from typing import Protocol, Self

from forecheck.domain.entities import Forecast, Observation, ScoreRecord, Station
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import ModelId, StationId, Variable


class Clock(Protocol):
    def now(self) -> datetime:
        """The current time, timezone-aware and in UTC."""
        ...


class ForecastSource(Protocol):
    """Today's forecasts, for the days ahead."""

    def fetch_forecasts(self, station: Station, issued_at: datetime) -> list[Forecast]:
        """Forecasts for every model and variable for the coming days, stamped ``issued_at``."""
        ...


class ForecastArchive(Protocol):
    """Forecasts as they stood at a fixed lead in the past, used to start with a history."""

    def fetch_archived_forecasts(self, station: Station, start: date, end: date) -> list[Forecast]:
        """Forecasts for the days ``start`` to ``end`` (inclusive), for leads 1 to 7."""
        ...


class ObservationSource(Protocol):
    """Station measurements, aggregated to UTC days."""

    def available_months(
        self, stations: Sequence[Station], start: date, end: date
    ) -> dict[date, str]:
        """The months in ``start``..``end`` the provider has data for, as first-of-month to a
        version string that changes whenever the provider republishes that month."""
        ...

    def fetch_observations(
        self, stations: Sequence[Station], start: date, end: date
    ) -> list[Observation]:
        """Daily figures for the days ``start`` to ``end`` (inclusive). Days that are missing or
        incomplete are left out."""
        ...


class ForecastRepository(Protocol):
    """Forecasts waiting for their measurement."""

    def upsert(self, forecasts: Sequence[Forecast]) -> None: ...

    def pending(self, up_to: date) -> list[Forecast]:
        """Forecasts whose valid day is on or before ``up_to``, oldest first."""
        ...

    def delete(self, forecasts: Sequence[Forecast]) -> None: ...

    def delete_valid_before(self, day: date) -> int:
        """Drop forecasts that will never be scored. Returns how many."""
        ...

    def earliest_valid_date(self) -> date | None: ...

    def count(self) -> int: ...


class ObservationRepository(Protocol):
    def upsert(self, observations: Sequence[Observation]) -> None: ...

    def between(self, start: date, end: date) -> list[Observation]:
        """Observations for the days ``start`` to ``end`` (inclusive)."""
        ...

    def latest_day(self) -> date | None: ...


class ScoreRepository(Protocol):
    def upsert(self, records: Sequence[ScoreRecord]) -> None:
        """Insert records, replacing any with the same station, model, variable, lead and day."""
        ...

    def latest_day(self) -> date | None: ...

    def by_lead(
        self, station_id: StationId, variable: Variable, since: date, until: date
    ) -> dict[ModelId, dict[int, ErrorStats]]:
        """Statistics summed over the days ``since`` to ``until``, per model and lead."""
        ...

    def by_station(
        self, variable: Variable, lead: int, since: date, until: date
    ) -> dict[StationId, dict[ModelId, ErrorStats]]:
        """One lead's statistics summed over ``since``..``until``, per station and model."""
        ...


class StateRepository(Protocol):
    """Small facts the app remembers between runs, such as which archive versions it has read."""

    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...


@dataclass(frozen=True, slots=True)
class RunRecord:
    kind: str
    at: datetime
    ok: bool
    message: str


class RunLogRepository(Protocol):
    def record(self, run: RunRecord) -> None: ...

    def latest(self, kind: str) -> RunRecord | None: ...


class UnitOfWork(Protocol):
    """One transaction across the repositories. Leaving the block without ``commit`` rolls back."""

    # Read-only properties, so an implementation may expose its own, narrower repository types.
    @property
    def forecasts(self) -> ForecastRepository: ...

    @property
    def observations(self) -> ObservationRepository: ...

    @property
    def scores(self) -> ScoreRepository: ...

    @property
    def state(self) -> StateRepository: ...

    @property
    def runs(self) -> RunLogRepository: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
