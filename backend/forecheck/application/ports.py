"""What the use cases need from the outside world. Adapters implement these."""

from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol

from forecheck.domain.entities import Forecast, Observation, Station


class Clock(Protocol):
    def now(self) -> datetime:
        """The current time, timezone-aware."""
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
