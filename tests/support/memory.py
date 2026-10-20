"""In-memory implementations of the repository ports, for fast tests.

They are held to the same contract tests as the PostgreSQL ones, so a use case that passes
against them can be trusted to behave the same against the real database.
"""

import copy
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from types import TracebackType
from typing import Self

from forecheck.application.ports import RunRecord
from forecheck.domain.entities import Forecast, Observation, ScoreRecord
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import ModelId, StationId, Variable


@dataclass
class State:
    forecasts: dict[tuple[str, str, str, date, int], Forecast] = field(default_factory=dict)
    observations: dict[tuple[str, str, date], Observation] = field(default_factory=dict)
    scores: dict[tuple[str, str, date, str, int], ScoreRecord] = field(default_factory=dict)
    state: dict[str, str] = field(default_factory=dict)
    runs: list[RunRecord] = field(default_factory=list)


class MemoryForecasts:
    def __init__(self, data: State) -> None:
        self._data = data

    def upsert(self, forecasts: Sequence[Forecast]) -> None:
        for f in forecasts:
            self._data.forecasts[
                (f.station_id, f.model, f.variable.value, f.valid_date, f.lead_days)
            ] = f

    def pending(self, up_to: date) -> list[Forecast]:
        return sorted(
            (f for f in self._data.forecasts.values() if f.valid_date <= up_to),
            key=lambda f: f.valid_date,
        )

    def delete(self, forecasts: Sequence[Forecast]) -> None:
        for f in forecasts:
            self._data.forecasts.pop(
                (f.station_id, f.model, f.variable.value, f.valid_date, f.lead_days), None
            )

    def delete_valid_before(self, day: date) -> int:
        doomed = [key for key, f in self._data.forecasts.items() if f.valid_date < day]
        for key in doomed:
            del self._data.forecasts[key]
        return len(doomed)

    def earliest_valid_date(self) -> date | None:
        return min((f.valid_date for f in self._data.forecasts.values()), default=None)

    def count(self) -> int:
        return len(self._data.forecasts)


class MemoryObservations:
    def __init__(self, data: State) -> None:
        self._data = data

    def upsert(self, observations: Sequence[Observation]) -> None:
        for o in observations:
            self._data.observations[(o.station_id, o.variable.value, o.day)] = o

    def between(self, start: date, end: date) -> list[Observation]:
        return [o for o in self._data.observations.values() if start <= o.day <= end]

    def latest_day(self) -> date | None:
        return max((o.day for o in self._data.observations.values()), default=None)


class MemoryScores:
    def __init__(self, data: State) -> None:
        self._data = data

    def upsert(self, records: Sequence[ScoreRecord]) -> None:
        for r in records:
            self._data.scores[
                (r.station_id, r.variable.value, r.valid_date, r.model, r.lead_days)
            ] = r

    def latest_day(self) -> date | None:
        return max((r.valid_date for r in self._data.scores.values()), default=None)

    def by_lead(
        self, station_id: StationId, variable: Variable, since: date, until: date
    ) -> dict[ModelId, dict[int, ErrorStats]]:
        result: dict[ModelId, dict[int, ErrorStats]] = defaultdict(dict)
        for r in self._data.scores.values():
            if (
                r.station_id == station_id
                and r.variable is variable
                and since <= r.valid_date <= until
            ):
                previous = result[r.model].get(r.lead_days, ErrorStats())
                result[r.model][r.lead_days] = previous + r.stats
        return dict(result)

    def by_station(
        self, variable: Variable, lead: int, since: date, until: date
    ) -> dict[StationId, dict[ModelId, ErrorStats]]:
        result: dict[StationId, dict[ModelId, ErrorStats]] = defaultdict(dict)
        for r in self._data.scores.values():
            if r.variable is variable and r.lead_days == lead and since <= r.valid_date <= until:
                previous = result[r.station_id].get(r.model, ErrorStats())
                result[r.station_id][r.model] = previous + r.stats
        return dict(result)


class MemoryState:
    def __init__(self, data: State) -> None:
        self._data = data

    def get(self, key: str) -> str | None:
        return self._data.state.get(key)

    def set(self, key: str, value: str) -> None:
        self._data.state[key] = value


class MemoryRuns:
    def __init__(self, data: State) -> None:
        self._data = data

    def record(self, run: RunRecord) -> None:
        self._data.runs.append(run)

    def latest(self, kind: str) -> RunRecord | None:
        matching = [r for r in self._data.runs if r.kind == kind]
        return max(matching, key=lambda r: r.at, default=None)


class MemoryDatabase:
    """The committed state. ``unit_of_work`` hands out transactions over it."""

    def __init__(self) -> None:
        self.committed = State()

    def unit_of_work(self) -> "MemoryUnitOfWork":
        return MemoryUnitOfWork(self)


class MemoryUnitOfWork:
    def __init__(self, database: MemoryDatabase) -> None:
        self._database = database
        self._working = State()

    def __enter__(self) -> Self:
        self._working = copy.deepcopy(self._database.committed)
        self.forecasts = MemoryForecasts(self._working)
        self.observations = MemoryObservations(self._working)
        self.scores = MemoryScores(self._working)
        self.state = MemoryState(self._working)
        self.runs = MemoryRuns(self._working)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._working = State()

    def commit(self) -> None:
        self._database.committed = copy.deepcopy(self._working)


def at(day: date, hour: int = 9) -> datetime:
    return datetime(day.year, day.month, day.day, hour, 0, tzinfo=UTC)
