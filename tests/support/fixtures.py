"""Loading and building the files the provider adapters read."""

import csv
import io
import json
import zipfile
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def json_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def text_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def bytes_fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def imgw_columns() -> list[str]:
    return next(csv.reader(io.StringIO(text_fixture("imgw_terminowe_header.csv").strip())))


def imgw_rows(archive: bytes) -> list[dict[str, str]]:
    """The rows of a sample archive, by column name."""
    columns = imgw_columns()
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        raw = zipped.read(zipped.namelist()[0]).decode("cp1250")
    return [dict(zip(columns, row, strict=True)) for row in csv.reader(io.StringIO(raw))]


def imgw_archive(rows: list[dict[str, str]], name: str = "s_t_09_2026.csv") -> bytes:
    """A zip like the ones IMGW publishes. Columns not named in a row stay empty."""
    columns = imgw_columns()
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    for row in rows:
        writer.writerow([row.get(column, "") for column in columns])
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as zipped:
        zipped.writestr(name, buffer.getvalue().encode("cp1250"))
    return output.getvalue()


def imgw_hour(
    nsp: str,
    day: str,
    hour: int,
    *,
    temp: str = "10.0",
    wind: str = "2",
    pressure: str = "1015.0",
    six_hour: tuple[str, str] = ("", "8"),
) -> dict[str, str]:
    """One hourly report. ``day`` is ``YYYY-MM-DD``. ``six_hour`` is (value, status) of WO6G."""
    year, month, date_of_month = day.split("-")
    return {
        "NSP": nsp,
        "POST": "TEST",
        "ROK": year,
        "MC": month,
        "DZ": date_of_month,
        "GG": f"{hour:02d}",
        "TEMP": temp,
        "FWR": wind,
        "PPPM": pressure,
        "WO6G": six_hour[0],
        "WWO6G": six_hour[1],
    }
