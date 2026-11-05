"""Checks what the data providers really give, and refreshes the test fixtures.

Run it from a machine that can reach the providers:

    uv run python scripts/explore_sources.py            # print the report
    uv run python scripts/explore_sources.py --write-fixtures

The report is what ``docs/data-sources.md`` is based on. Every claim the method
rests on is a line in it, so a change at a provider shows up as a changed report.
It makes about a dozen requests.
"""

import argparse
import csv
import io
import json
import sys
import zipfile
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from forecheck.application.catalog import DEFAULT_CATALOG
from forecheck.application.errors import SourceError
from forecheck.domain.types import Variable
from forecheck.infrastructure import imgw, open_meteo
from forecheck.infrastructure.http import HttpClient

FIXTURES = ROOT / "tests" / "fixtures"
UA = "forecheck-explore/0.1"


def say(line: str = "") -> None:
    print(line, flush=True)


def explore_imgw_live(http: HttpClient) -> None:
    say("## IMGW live API (https://danepubliczne.imgw.pl/api/data/synop)")
    rows: list[dict[str, str]] = http.get_json("https://danepubliczne.imgw.pl/api/data/synop")
    ids = {row["id_stacji"] for row in rows}
    say(f"- stations returned: {len(rows)}; fields: {sorted(rows[0])}")
    say(
        f"- observation time of the first row: {rows[0]['data_pomiaru']} {rows[0]['godzina_pomiaru']}h"
    )
    say("- it returns the latest hourly report only. History needs the archive.")
    for station in DEFAULT_CATALOG.stations:
        say(
            f"- catalog station {station.id} {station.name}: {'present' if station.id in ids else 'MISSING'}"
        )
    say(f"- Debica has a synoptic station: {any('bica' in row['stacja'].lower() for row in rows)}")


def explore_imgw_archive(http: HttpClient, write: bool) -> None:
    say("\n## IMGW hourly archive (terminowe/synop)")
    archive = imgw.ImgwSynopArchive(http)
    today = datetime.now(UTC).date()
    stations = list(DEFAULT_CATALOG.stations)

    listing_year = archive._listing(today.year)
    say(f"- files in {today.year}: {len(listing_year)}; e.g. {sorted(listing_year.items())[-3:]}")
    previous = archive._listing(today.year - 1)
    say(
        f"- files in {today.year - 1}: {len(previous)} (per-station yearly zips: {sorted(previous)[:2]})"
    )

    months = archive.available_months(stations, date(today.year, 1, 1), today)
    last = max(months)
    month_end = (last + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    say(f"- latest month available: {last:%Y-%m}, published {months[last]}; today is {today}")
    say(f"- lag: that month ended {month_end}, the file was published {months[last][:10]}")

    observations = archive.fetch_observations(stations, last, month_end - timedelta(days=1))
    frame = pd.DataFrame(
        [
            {"station": o.station_id, "variable": o.variable.value, "day": o.day, "value": o.value}
            for o in observations
        ]
    )
    expected_days = (month_end - last).days
    table = (
        frame.pivot_table(index="station", columns="variable", values="day", aggfunc="count")
        .fillna(0)
        .astype(int)
    )
    say(f"- complete days per station and variable (of {expected_days}):")
    say("```\n" + table.to_string() + "\n```")
    ranges = frame.groupby("variable")["value"].agg(["min", "max"]).round(1)
    say("- value ranges (sanity check of units):")
    say("```\n" + ranges.to_string() + "\n```")

    if write:
        write_imgw_fixtures(http, archive, last)


def write_imgw_fixtures(http: HttpClient, archive: imgw.ImgwSynopArchive, month: date) -> None:
    path = f"{month.year}/{month.year}_{month.month:02d}_s.zip"
    with zipfile.ZipFile(io.BytesIO(http.get_bytes(f"{imgw.BASE_URL}/{path}"))) as source:
        name = source.namelist()[0]
        raw = source.read(name).decode("cp1250")
    columns = archive._header()
    keep_codes = {"566", "580"}  # Krakow and Rzeszow
    kept = [
        row
        for row in csv.reader(io.StringIO(raw))
        if row[columns["NSP"]][-3:] in keep_codes and int(row[columns["DZ"]]) <= 4
    ]
    buffer = io.StringIO()
    csv.writer(
        buffer, lineterminator="\r\n", quoting=csv.QUOTE_NONNUMERIC if False else csv.QUOTE_MINIMAL
    ).writerows(kept)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        FIXTURES / "imgw_terminowe_synop_sample.zip", "w", zipfile.ZIP_DEFLATED
    ) as target:
        target.writestr(name, buffer.getvalue().encode("cp1250"))
    (FIXTURES / "imgw_terminowe_header.csv").write_text(
        http.get_text(imgw.HEADER_URL), encoding="utf-8"
    )
    (FIXTURES / "imgw_listing_sample.html").write_text(
        http.get_text(f"{imgw.BASE_URL}/{month.year}/"), encoding="utf-8"
    )
    say(f"- wrote IMGW fixtures from {path} ({len(kept)} rows kept)")


def explore_open_meteo(http: HttpClient, write: bool) -> None:
    say("\n## Open-Meteo forecast API")
    station = next(s for s in DEFAULT_CATALOG.stations if s.name == "Kraków")
    models = DEFAULT_CATALOG.provider_names
    source = open_meteo.OpenMeteo(http, models)
    issued_at = datetime.now(UTC)
    forecasts = source.fetch_forecasts(station, issued_at)
    frame = pd.DataFrame(
        [
            {
                "model": f.model,
                "variable": f.variable.value,
                "lead": f.lead_days,
                "value": f.value,
                "probability": f.probability,
            }
            for f in forecasts
        ]
    )
    say(f"- forecasts parsed: {len(forecasts)} (3 models x 4 variables x leads 1-7 = 84 expected)")
    rain = frame[frame.variable == Variable.PRECIPITATION.value]
    say("- precipitation probability present per model (non-null / total):")
    say(
        "```\n"
        + rain.groupby("model")["probability"]
        .agg(lambda s: f"{s.notna().sum()}/{len(s)}")
        .to_string()
        + "\n```"
    )
    say(
        "- caveat: the probability is the daily MAXIMUM of the hourly chance, not the chance of >=0.1 mm in the day."
    )
    if write:
        payload: Any = http.get_json(
            open_meteo.FORECAST_URL,
            {
                "latitude": station.latitude,
                "longitude": station.longitude,
                "daily": "temperature_2m_mean,precipitation_sum,precipitation_probability_max,"
                "wind_speed_10m_mean,pressure_msl_mean",
                "models": ",".join(models.values()),
                "forecast_days": 8,
                "timezone": "UTC",
                "wind_speed_unit": "ms",
            },
        )
        (FIXTURES / "open_meteo_forecast.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        say("- wrote tests/fixtures/open_meteo_forecast.json")


def explore_previous_runs(http: HttpClient) -> None:
    say("\n## Open-Meteo Previous Runs API (backfill)")
    station = next(s for s in DEFAULT_CATALOG.stations if s.name == "Kraków")
    source = open_meteo.OpenMeteo(http, DEFAULT_CATALOG.provider_names)
    end = datetime.now(UTC).date() - timedelta(days=10)
    archived = source.fetch_archived_forecasts(station, end - timedelta(days=4), end)
    say(
        f"- archived forecasts parsed for 5 days: {len(archived)} (5 days x 3 models x 4 variables x 7 leads = 420)"
    )
    say(
        "- daily variables are rejected (HTTP 400): the adapter asks for hourly ones and builds the days"
    )
    say("- the API needs no key and no payment on the free non-commercial tier")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--write-fixtures",
        action="store_true",
        help="refresh tests/fixtures from the live responses",
    )
    args = parser.parse_args()
    http = HttpClient(user_agent=UA)
    say(f"# Source exploration, {datetime.now(UTC):%Y-%m-%d %H:%M} UTC")
    steps = (
        lambda: explore_imgw_live(http),
        lambda: explore_imgw_archive(http, args.write_fixtures),
        lambda: explore_open_meteo(http, args.write_fixtures),
        lambda: explore_previous_runs(http),
    )
    for step in steps:
        try:
            step()
        except SourceError as error:
            say(f"- FAILED: {error}")


if __name__ == "__main__":
    main()
