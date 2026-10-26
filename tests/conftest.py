"""Fixtures shared by all tests: a clean PostgreSQL, and the same repositories in memory."""

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text

from forecheck.application.ports import UnitOfWorkFactory
from forecheck.infrastructure.db.engine import create_db_engine
from forecheck.infrastructure.db.unit_of_work import PgUnitOfWork
from tests.support.memory import MemoryDatabase

TABLES = ("forecasts", "observations", "scores", "source_state", "runs")


def _test_database_url() -> str | None:
    return os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def pg_engine() -> Iterator[Engine]:
    """A migrated test database. Skips the tests that need it when none is configured."""
    url = _test_database_url()
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    os.environ["DIRECT_URL"] = url
    config = Config("alembic.ini")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_db_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def pg_uow_factory(pg_engine: Engine) -> UnitOfWorkFactory:
    with pg_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY"))
    return lambda: PgUnitOfWork(pg_engine)


@pytest.fixture(params=["memory", "postgres"])
def uow_factory(request: pytest.FixtureRequest) -> UnitOfWorkFactory:
    """The same suite runs against both implementations of the ports."""
    if request.param == "memory":
        return MemoryDatabase().unit_of_work
    factory: UnitOfWorkFactory = request.getfixturevalue("pg_uow_factory")
    return factory
