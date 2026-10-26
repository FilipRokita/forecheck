"""Against a real PostgreSQL (``TEST_DATABASE_URL``): the schema, and the pipeline end to end."""

from datetime import date

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine

from forecheck.application.ports import UnitOfWorkFactory
from forecheck.application.use_cases.collect_forecasts import CollectForecasts
from forecheck.application.use_cases.evaluate_forecasts import EvaluateForecasts
from forecheck.application.use_cases.ingest_observations import IngestObservations
from forecheck.application.use_cases.run_daily_cycle import RunDailyCycle
from forecheck.domain.rules import Rules
from forecheck.domain.types import ModelId, Variable
from forecheck.infrastructure.db.tables import metadata
from tests.unit.application.fakes import FakeForecastSource, FakeObservationSource, clock_at
from tests.unit.application.test_cycle_backfill_reports import CATALOG, KRAKOW


def test_the_migrations_build_exactly_the_schema_the_code_expects(pg_engine: Engine) -> None:
    with pg_engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), metadata)
    assert differences == []


def test_the_daily_cycle_runs_end_to_end_on_postgres(pg_uow_factory: UnitOfWorkFactory) -> None:
    clock = clock_at(2026, 9, 1)
    forecasts = FakeForecastSource(value=10.0, models=("icon", "ecmwf"), variables=tuple(Variable))
    observations = FakeObservationSource({}, value=11.0)
    job = RunDailyCycle(
        CollectForecasts(forecasts, pg_uow_factory, clock, CATALOG),
        IngestObservations(observations, pg_uow_factory, clock, CATALOG),
        EvaluateForecasts(pg_uow_factory, clock, Rules(min_samples=2)),
        pg_uow_factory,
        clock,
    )
    for _ in range(5):
        assert job.run().ok
        clock.advance(1)

    observations.months[date(2026, 9, 1)] = "published"
    clock.advance(30)
    assert job.run().ok

    with pg_uow_factory() as uow:
        latest = uow.scores.latest_day()
        assert latest is not None
        totals = uow.scores.by_lead(KRAKOW.id, Variable.TEMPERATURE, date(2026, 9, 1), latest)
        assert {lead: stats.n for lead, stats in totals[ModelId("icon")].items()}[1] > 0
        assert uow.runs.latest("evaluate") is not None
