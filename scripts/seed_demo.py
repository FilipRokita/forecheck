"""Fills a LOCAL database with made-up scores, so the interface can be developed without waiting
for real data. The page shows a "Sample data" badge while they are there.

    uv run python scripts/seed_demo.py            # write demo scores
    uv run python scripts/seed_demo.py --clear    # remove all scores and the demo flag

Never run it against a real deployment: it refuses a database that already holds scores that it did
not write, unless --force is given.
"""

import argparse
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import delete

from forecheck.application.catalog import DEFAULT_CATALOG
from forecheck.application.queries import SAMPLE_DATA_KEY
from forecheck.domain.entities import ScoreRecord
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import Variable
from forecheck.infrastructure.db import tables
from forecheck.infrastructure.db.engine import create_db_engine
from forecheck.infrastructure.db.unit_of_work import PgUnitOfWork
from forecheck.infrastructure.settings import Settings

DAYS = 120
# Typical error at lead 1, and how it grows per extra day, per variable. Invented, not measured.
BASE_ERROR = {
    Variable.TEMPERATURE: (1.0, 0.45),
    Variable.WIND: (0.9, 0.22),
    Variable.PRESSURE: (0.8, 0.5),
    Variable.PRECIPITATION: (0.0, 0.0),
}
SKILL = {"icon": 1.08, "ecmwf": 1.0, "gfs": 1.35}


def records(seed: int = 7) -> list[ScoreRecord]:
    rng = random.Random(seed)
    last = date.today() - timedelta(days=14)
    found: list[ScoreRecord] = []
    for station in DEFAULT_CATALOG.stations:
        station_factor = rng.uniform(0.85, 1.2)
        for model in DEFAULT_CATALOG.models:
            for variable in Variable:
                for lead in range(1, 8):
                    for offset in range(DAYS):
                        day = last - timedelta(days=offset)
                        found.append(
                            ScoreRecord(
                                station.id, model.id, variable, lead, day,
                                one_day(rng, variable, lead, SKILL[model.id] * station_factor),
                            )
                        )  # fmt: skip
    return found


def one_day(rng: random.Random, variable: Variable, lead: int, skill: float) -> ErrorStats:
    if variable is Variable.PRECIPITATION:
        right = rng.random() < max(0.5, 0.93 - 0.05 * (lead - 1) * skill)
        wet = rng.random() < 0.4
        return ErrorStats(
            n=1,
            abs_error_sum=0.0 if right else rng.uniform(0.2, 6.0),
            hits=int(right and wet),
            misses=int(not right and wet),
            false_alarms=int(not right and not wet),
            correct_negatives=int(right and not wet),
            brier_sum=rng.uniform(0.0, 0.15) if right else rng.uniform(0.3, 0.8),
            brier_n=1,
        )
    base, growth = BASE_ERROR[variable]
    error = abs(rng.gauss(0, 1)) * (base + growth * (lead - 1)) * skill * 0.8 + 0.1
    signed = error if rng.random() < 0.5 else -error
    return ErrorStats(n=1, abs_error_sum=error, error_sum=signed, squared_error_sum=error * error)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--clear", action="store_true", help="remove all scores and the demo flag")
    parser.add_argument("--force", action="store_true", help="write even if real scores exist")
    args = parser.parse_args()

    settings = Settings()
    if not settings.database_url:
        sys.exit("DATABASE_URL is not set. Copy .env.example to .env first.")
    engine = create_db_engine(settings.database_url)

    with PgUnitOfWork(engine) as uow:
        flagged = uow.state.get(SAMPLE_DATA_KEY) == "1"
        has_scores = uow.scores.latest_day() is not None
        if args.clear:
            uow._connection.execute(delete(tables.scores))  # type: ignore[attr-defined]
            uow.state.set(SAMPLE_DATA_KEY, "0")
            uow.commit()
            print("Scores removed.")
            return
        if has_scores and not flagged and not args.force:
            sys.exit(
                "The database holds real scores. Refusing to mix demo data in (use --force to override)."
            )
        uow.scores.upsert(records())
        uow.state.set(SAMPLE_DATA_KEY, "1")
        uow.commit()
    print(
        f"Wrote demo scores for {len(DEFAULT_CATALOG.stations)} stations. The page now shows a 'Sample data' badge."
    )


if __name__ == "__main__":
    main()
