"""The composition root: where adapters are chosen and wired into the use cases."""

import time
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import Engine

from forecheck.application.catalog import DEFAULT_CATALOG, Catalog
from forecheck.application.queries import Reports
from forecheck.application.use_cases.backfill_scores import BackfillScores
from forecheck.application.use_cases.collect_forecasts import CollectForecasts
from forecheck.application.use_cases.evaluate_forecasts import EvaluateForecasts
from forecheck.application.use_cases.ingest_observations import IngestObservations
from forecheck.application.use_cases.run_daily_cycle import RunDailyCycle
from forecheck.infrastructure.clock import SystemClock
from forecheck.infrastructure.db.engine import create_db_engine
from forecheck.infrastructure.db.unit_of_work import PgUnitOfWork
from forecheck.infrastructure.http import HttpClient
from forecheck.infrastructure.imgw import ImgwSynopArchive
from forecheck.infrastructure.open_meteo import OpenMeteo
from forecheck.infrastructure.settings import Settings

# Open-Meteo asks for restraint: one request a second is far below its limits.
_PAUSE_SECONDS = 1.0


@dataclass(frozen=True)
class Services:
    settings: Settings
    catalog: Catalog
    reports: Reports
    daily_cycle: RunDailyCycle
    backfill: BackfillScores


def build_services(
    settings: Settings, engine: Engine, catalog: Catalog = DEFAULT_CATALOG
) -> Services:
    rules = settings.rules()
    clock = SystemClock()
    uow_factory = lambda: PgUnitOfWork(engine)  # noqa: E731 - the factory is the unit of work's constructor
    http = HttpClient(user_agent=settings.user_agent)
    open_meteo = OpenMeteo(http, catalog.provider_names)
    imgw = ImgwSynopArchive(http)

    def pause() -> None:
        time.sleep(_PAUSE_SECONDS)

    ingest = IngestObservations(imgw, uow_factory, clock, catalog)
    return Services(
        settings=settings,
        catalog=catalog,
        reports=Reports(uow_factory, catalog, rules),
        daily_cycle=RunDailyCycle(
            CollectForecasts(open_meteo, uow_factory, clock, catalog, pause=pause),
            ingest,
            EvaluateForecasts(uow_factory, clock, rules),
            uow_factory,
            clock,
        ),
        backfill=BackfillScores(open_meteo, ingest, uow_factory, catalog, rules, pause=pause),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Read from the environment once. Cheap, so a route that needs only a setting (the cron
    secret) can check it before anything else is built."""
    return Settings()


@lru_cache(maxsize=1)
def get_services() -> Services:
    """Built on first use and kept for the life of the process (a warm serverless instance)."""
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set.")
    return build_services(settings, create_db_engine(settings.database_url))
