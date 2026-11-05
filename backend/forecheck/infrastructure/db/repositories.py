"""PostgreSQL implementations of the repository ports."""

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime
from itertools import batched
from typing import Any

from sqlalchemy import Connection, Table, delete, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert

from forecheck.application.ports import RunRecord
from forecheck.domain.entities import Forecast, Observation, ScoreRecord
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import ModelId, StationId, Variable
from forecheck.infrastructure.db import tables

# psycopg sends at most 65,535 parameters per statement.
_CHUNK = 1000


def _upsert(
    connection: Connection, table: Table, rows: Sequence[dict[str, Any]], *, keys: Sequence[str]
) -> None:
    """Insert ``rows``, replacing the non-key columns of any row that already exists."""
    for chunk in batched(rows, _CHUNK, strict=False):
        statement = insert(table).values(list(chunk))
        replaceable = {
            c.name: statement.excluded[c.name] for c in table.columns if c.name not in keys
        }
        connection.execute(
            statement.on_conflict_do_update(index_elements=list(keys), set_=replaceable)
        )


def _insert_missing(
    connection: Connection, table: Table, rows: Sequence[dict[str, Any]], *, keys: Sequence[str]
) -> int:
    """Insert the ``rows`` that do not exist yet and leave the others. Returns how many went in."""
    inserted = 0
    for chunk in batched(rows, _CHUNK, strict=False):
        statement = (
            insert(table)
            .values(list(chunk))
            .on_conflict_do_nothing(index_elements=list(keys))
            .returning(table.c[keys[0]])
        )
        inserted += len(connection.execute(statement).all())
    return inserted


class PgForecastRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def upsert(self, forecasts: Sequence[Forecast]) -> None:
        _upsert(
            self._connection,
            tables.forecasts,
            [
                {
                    "station_id": f.station_id,
                    "model": f.model,
                    "variable": f.variable.value,
                    "valid_date": f.valid_date,
                    "lead_days": f.lead_days,
                    "issued_at": f.issued_at,
                    "value": f.value,
                    "probability": f.probability,
                }
                for f in forecasts
            ],
            keys=("station_id", "model", "variable", "valid_date", "lead_days"),
        )

    def pending(self, up_to: date) -> list[Forecast]:
        rows = self._connection.execute(
            select(tables.forecasts)
            .where(tables.forecasts.c.valid_date <= up_to)
            .order_by(tables.forecasts.c.valid_date)
        )
        return [
            Forecast(
                station_id=StationId(row.station_id),
                model=ModelId(row.model),
                variable=Variable(row.variable),
                valid_date=row.valid_date,
                issued_at=row.issued_at,
                value=row.value,
                probability=row.probability,
            )
            for row in rows
        ]

    def delete(self, forecasts: Sequence[Forecast]) -> None:
        columns = tables.forecasts.c
        key = tuple_(
            columns.station_id,
            columns.model,
            columns.variable,
            columns.valid_date,
            columns.lead_days,
        )
        for chunk in batched(forecasts, _CHUNK, strict=False):
            keys = [
                (f.station_id, f.model, f.variable.value, f.valid_date, f.lead_days) for f in chunk
            ]
            self._connection.execute(delete(tables.forecasts).where(key.in_(keys)))

    def delete_valid_before(self, day: date) -> int:
        result = self._connection.execute(
            delete(tables.forecasts).where(tables.forecasts.c.valid_date < day)
        )
        return result.rowcount

    def earliest_valid_date(self) -> date | None:
        return self._connection.execute(select(func.min(tables.forecasts.c.valid_date))).scalar()

    def count(self) -> int:
        return int(
            self._connection.execute(
                select(func.count()).select_from(tables.forecasts)
            ).scalar_one()
        )


class PgObservationRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def upsert(self, observations: Sequence[Observation]) -> None:
        _upsert(
            self._connection,
            tables.observations,
            [
                {
                    "station_id": o.station_id,
                    "variable": o.variable.value,
                    "day": o.day,
                    "value": o.value,
                }
                for o in observations
            ],
            keys=("station_id", "variable", "day"),
        )

    def between(self, start: date, end: date) -> list[Observation]:
        rows = self._connection.execute(
            select(tables.observations).where(tables.observations.c.day.between(start, end))
        )
        return [
            Observation(StationId(r.station_id), Variable(r.variable), r.day, r.value) for r in rows
        ]

    def latest_day(self) -> date | None:
        return self._connection.execute(select(func.max(tables.observations.c.day))).scalar()


_STAT_COLUMNS = (
    "n",
    "abs_error_sum",
    "error_sum",
    "squared_error_sum",
    "hits",
    "misses",
    "false_alarms",
    "correct_negatives",
    "brier_sum",
    "brier_n",
)


def _sums() -> list[Any]:
    return [func.sum(tables.scores.c[name]).label(name) for name in _STAT_COLUMNS]


def _stats(row: Any) -> ErrorStats:
    return ErrorStats(
        **{name: type(getattr(ErrorStats(), name))(getattr(row, name)) for name in _STAT_COLUMNS}
    )


class PgScoreRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    _KEYS = ("station_id", "variable", "valid_date", "model", "lead_days")

    @staticmethod
    def _rows(records: Sequence[ScoreRecord]) -> list[dict[str, Any]]:
        return [
            {
                "station_id": r.station_id,
                "variable": r.variable.value,
                "valid_date": r.valid_date,
                "model": r.model,
                "lead_days": r.lead_days,
                **{name: getattr(r.stats, name) for name in _STAT_COLUMNS},
            }
            for r in records
        ]

    def upsert(self, records: Sequence[ScoreRecord]) -> None:
        _upsert(self._connection, tables.scores, self._rows(records), keys=self._KEYS)

    def insert_missing(self, records: Sequence[ScoreRecord]) -> int:
        return _insert_missing(
            self._connection, tables.scores, self._rows(records), keys=self._KEYS
        )

    def latest_day(self) -> date | None:
        return self._connection.execute(select(func.max(tables.scores.c.valid_date))).scalar()

    def by_lead(
        self, station_id: StationId, variable: Variable, since: date, until: date
    ) -> dict[ModelId, dict[int, ErrorStats]]:
        rows = self._connection.execute(
            select(tables.scores.c.model, tables.scores.c.lead_days, *_sums())
            .where(
                tables.scores.c.station_id == station_id,
                tables.scores.c.variable == variable.value,
                tables.scores.c.valid_date.between(since, until),
            )
            .group_by(tables.scores.c.model, tables.scores.c.lead_days)
        )
        result: dict[ModelId, dict[int, ErrorStats]] = defaultdict(dict)
        for row in rows:
            result[ModelId(row.model)][int(row.lead_days)] = _stats(row)
        return dict(result)

    def by_station(
        self, variable: Variable, lead: int, since: date, until: date
    ) -> dict[StationId, dict[ModelId, ErrorStats]]:
        rows = self._connection.execute(
            select(tables.scores.c.station_id, tables.scores.c.model, *_sums())
            .where(
                tables.scores.c.variable == variable.value,
                tables.scores.c.lead_days == lead,
                tables.scores.c.valid_date.between(since, until),
            )
            .group_by(tables.scores.c.station_id, tables.scores.c.model)
        )
        result: dict[StationId, dict[ModelId, ErrorStats]] = defaultdict(dict)
        for row in rows:
            result[StationId(row.station_id)][ModelId(row.model)] = _stats(row)
        return dict(result)


class PgStateRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get(self, key: str) -> str | None:
        return self._connection.execute(
            select(tables.source_state.c.value).where(tables.source_state.c.key == key)
        ).scalar()

    def set(self, key: str, value: str) -> None:
        _upsert(
            self._connection,
            tables.source_state,
            [{"key": key, "value": value, "updated_at": datetime.now(UTC)}],
            keys=("key",),
        )


class PgRunLogRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def record(self, run: RunRecord) -> None:
        self._connection.execute(
            insert(tables.runs).values(kind=run.kind, at=run.at, ok=run.ok, message=run.message)
        )

    def latest(self, kind: str) -> RunRecord | None:
        row = self._connection.execute(
            select(tables.runs)
            .where(tables.runs.c.kind == kind)
            .order_by(tables.runs.c.at.desc())
            .limit(1)
        ).first()
        return None if row is None else RunRecord(row.kind, row.at, row.ok, row.message)
