"""One database transaction across all repositories."""

from types import TracebackType
from typing import Self

from sqlalchemy import Connection, Engine

from forecheck.infrastructure.db.repositories import (
    PgForecastRepository,
    PgObservationRepository,
    PgRunLogRepository,
    PgScoreRepository,
    PgStateRepository,
)


class PgUnitOfWork:
    """Opens a connection on entry and rolls back on exit unless ``commit`` was called."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._connection: Connection | None = None

    def __enter__(self) -> Self:
        self._connection = self._engine.connect()
        self.forecasts = PgForecastRepository(self._connection)
        self.observations = PgObservationRepository(self._connection)
        self.scores = PgScoreRepository(self._connection)
        self.state = PgStateRepository(self._connection)
        self.runs = PgRunLogRepository(self._connection)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._connection is not None:
            self._connection.close()  # an open transaction is rolled back
            self._connection = None

    def commit(self) -> None:
        if self._connection is None:
            raise RuntimeError("commit() outside of the unit of work")
        self._connection.commit()
