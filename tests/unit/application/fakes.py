"""Stand-ins for the outside world, for use case tests."""

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from forecheck.application.errors import RateLimitedError, SourceUnavailableError
from forecheck.domain.entities import Forecast, Observation, Station
from forecheck.domain.types import ModelId, StationId, Variable


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, days: int) -> None:
        self._now += timedelta(days=days)


def clock_at(year: int, month: int, day: int, hour: int = 9) -> FakeClock:
    return FakeClock(datetime(year, month, day, hour, 0, tzinfo=UTC))


class FakeForecastSource:
    """Gives every station the same constant forecasts, unless told to fail."""

    def __init__(
        self,
        value: float = 10.0,
        *,
        models: Sequence[str] = ("icon", "ecmwf", "gfs"),
        variables: Sequence[Variable] = (Variable.TEMPERATURE,),
        failing: Sequence[str] = (),
        rate_limited_at: str | None = None,
    ) -> None:
        self.value = value
        self._models = models
        self._variables = variables
        self._failing = set(failing)
        self._rate_limited_at = rate_limited_at
        self.requested: list[str] = []

    def fetch_forecasts(self, station: Station, issued_at: datetime) -> list[Forecast]:
        self.requested.append(station.id)
        if station.id == self._rate_limited_at:
            raise RateLimitedError("Daily API request limit exceeded")
        if station.id in self._failing:
            raise SourceUnavailableError("down")
        today = issued_at.astimezone(UTC).date()
        return [
            Forecast(
                station.id,
                ModelId(model),
                variable,
                today + timedelta(days=lead),
                issued_at,
                self.value,
            )
            for model in self._models
            for variable in self._variables
            for lead in range(1, 8)
        ]


class FakeObservationSource:
    """Serves measurements from a dict, month by month, and counts the reads."""

    def __init__(self, months: dict[date, str], value: float = 11.0) -> None:
        self.months = months
        self.value = value
        self.fetches: list[tuple[date, date]] = []

    def available_months(
        self, stations: Sequence[Station], start: date, end: date
    ) -> dict[date, str]:
        return {m: v for m, v in self.months.items() if start.replace(day=1) <= m <= end}

    def fetch_observations(
        self, stations: Sequence[Station], start: date, end: date
    ) -> list[Observation]:
        self.fetches.append((start, end))
        found: list[Observation] = []
        day = start
        while day <= end:
            found.extend(Observation(s.id, Variable.TEMPERATURE, day, self.value) for s in stations)
            day += timedelta(days=1)
        return found


class FakeArchive:
    def __init__(self, value: float = 10.0, models: Sequence[str] = ("icon", "ecmwf")) -> None:
        self.value = value
        self._models = models
        self.calls: list[StationId] = []

    def fetch_archived_forecasts(self, station: Station, start: date, end: date) -> list[Forecast]:
        self.calls.append(station.id)
        found: list[Forecast] = []
        day = start
        while day <= end:
            for model in self._models:
                for lead in range(1, 8):
                    issued = datetime(day.year, day.month, day.day, tzinfo=UTC) - timedelta(
                        days=lead
                    )
                    found.append(
                        Forecast(
                            station.id,
                            ModelId(model),
                            Variable.TEMPERATURE,
                            day,
                            issued,
                            self.value,
                        )
                    )
            day += timedelta(days=1)
        return found
