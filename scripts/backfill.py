"""Starts the app with a history: scores archived forecasts against IMGW measurements.

    uv run python scripts/backfill.py --days 60
    uv run python scripts/backfill.py --start 2026-07-01 --end 2026-08-31 --stations 12566 12580

Run it by hand, once, on your own machine (it reads DATABASE_URL from .env), never from the
scheduled job. It uses the Open-Meteo Previous Runs API, which is free for non-commercial use,
and makes one request per station and 31 days. The default window ends at the newest IMGW month
already published, because older forecasts cannot be scored without measurements.

Safe to repeat: scores are keyed by station, variable, day, model and lead, and one that already
exists (for example from a live forecast) is kept.
"""

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from forecheck.application.errors import SourceError
from forecheck.domain.types import StationId
from forecheck.entrypoints.composition import build_services
from forecheck.infrastructure.db.engine import create_db_engine
from forecheck.infrastructure.http import HttpClient
from forecheck.infrastructure.imgw import ImgwSynopArchive
from forecheck.infrastructure.settings import Settings


def newest_published_day(services_imgw_months: dict[date, str]) -> date | None:
    if not services_imgw_months:
        return None
    month = max(services_imgw_months)
    return (month + timedelta(days=32)).replace(day=1) - timedelta(days=1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--days", type=int, default=60, help="how many days back from the end (default 60)"
    )
    parser.add_argument(
        "--start", type=date.fromisoformat, help="first day, YYYY-MM-DD (overrides --days)"
    )
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        help="last day, YYYY-MM-DD (default: end of the newest published IMGW month)",
    )
    parser.add_argument("--stations", nargs="*", help="only these IMGW station ids")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = Settings()
    if not settings.database_url:
        sys.exit("DATABASE_URL is not set. Copy .env.example to .env first.")
    services = build_services(settings, create_db_engine(settings.database_url))

    end = args.end
    if end is None:
        imgw = ImgwSynopArchive(HttpClient(user_agent=settings.user_agent))
        today = date.today()
        end = newest_published_day(
            imgw.available_months(services.catalog.stations, today - timedelta(days=120), today)
        )
        if end is None:
            sys.exit("IMGW has published no month in the last 120 days.")
    start = args.start or end - timedelta(days=args.days - 1)
    only = [StationId(s) for s in args.stations] if args.stations else None

    print(
        f"Backfilling {start} to {end} for {len(only) if only else len(services.catalog.stations)} stations..."
    )
    try:
        report = services.backfill.run(start, end, only)
    except SourceError as error:
        sys.exit(
            f"Stopped: {error}\nWhat was scored so far is saved. Run it again to continue (it is safe to repeat)."
        )
    print(f"Done: {report.observations} observations read, {report.scored} scores written.")


if __name__ == "__main__":
    main()
