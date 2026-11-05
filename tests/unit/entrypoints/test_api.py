import csv
import io
from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from forecheck.application import attribution
from forecheck.application.queries import Reports
from forecheck.application.use_cases.backfill_scores import BackfillScores
from forecheck.application.use_cases.collect_forecasts import CollectForecasts
from forecheck.application.use_cases.evaluate_forecasts import EvaluateForecasts
from forecheck.application.use_cases.ingest_observations import IngestObservations
from forecheck.application.use_cases.run_daily_cycle import RunDailyCycle
from forecheck.domain.entities import ScoreRecord
from forecheck.domain.rules import Rules
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import ModelId, StationId, Variable
from forecheck.entrypoints.composition import Services, get_services, get_settings
from forecheck.entrypoints.http.app import create_app
from forecheck.infrastructure.settings import Settings
from tests.support.memory import MemoryDatabase
from tests.unit.application.fakes import (
    FakeArchive,
    FakeForecastSource,
    FakeObservationSource,
    clock_at,
)
from tests.unit.application.test_cycle_backfill_reports import CATALOG, KRAKOW, RULES

LAST_DAY = date(2026, 9, 30)


def seed(database: MemoryDatabase, variable: Variable = Variable.TEMPERATURE) -> None:
    records = []
    for model, error in (("icon", 1.2), ("ecmwf", 1.0)):
        for offset in range(30):
            for lead in range(1, 6):
                stats = ErrorStats(
                    n=1,
                    abs_error_sum=error * lead / 2,
                    error_sum=error * lead / 2,
                    squared_error_sum=error,
                )
                if variable is Variable.PRECIPITATION:
                    stats += ErrorStats(hits=1, brier_sum=0.1, brier_n=1)
                records.append(
                    ScoreRecord(
                        KRAKOW.id,
                        ModelId(model),
                        variable,
                        lead,
                        LAST_DAY - timedelta(days=offset),
                        stats,
                    )
                )
    with database.unit_of_work() as uow:
        uow.scores.upsert(records)
        uow.commit()


def make_services(
    database: MemoryDatabase, *, cron_secret: str = "s3cret", rate_limited: bool = False
) -> Services:
    clock = clock_at(2026, 10, 20)
    source = FakeForecastSource(rate_limited_at=KRAKOW.id if rate_limited else None)
    ingest = IngestObservations(FakeObservationSource({}), database.unit_of_work, clock, CATALOG)
    return Services(
        settings=Settings(cron_secret=cron_secret, _env_file=None),
        catalog=CATALOG,
        reports=Reports(database.unit_of_work, CATALOG, RULES),
        daily_cycle=RunDailyCycle(
            CollectForecasts(source, database.unit_of_work, clock, CATALOG),
            ingest,
            EvaluateForecasts(database.unit_of_work, clock, RULES),
            database.unit_of_work,
            clock,
        ),
        backfill=BackfillScores(FakeArchive(), ingest, database.unit_of_work, CATALOG, RULES),
    )


def serve(app: FastAPI, services: Services) -> None:
    app.dependency_overrides[get_services] = lambda: services
    app.dependency_overrides[get_settings] = lambda: services.settings


@pytest.fixture
def database() -> MemoryDatabase:
    database = MemoryDatabase()
    seed(database)
    return database


@pytest.fixture
def client(database: MemoryDatabase) -> Iterator[TestClient]:
    app = create_app()
    serve(app, make_services(database))
    with TestClient(app) as test_client:
        yield test_client


def test_meta_describes_what_can_be_asked(client: TestClient) -> None:
    body = client.get("/api/meta").json()
    assert [s["id"] for s in body["stations"]] == ["12566", "12580"]
    assert [m["id"] for m in body["models"]] == ["icon", "ecmwf"]
    assert [v["id"] for v in body["variables"]] == [
        "temperature",
        "precipitation",
        "wind",
        "pressure",
    ]
    assert {v["id"]: v["metric"] for v in body["variables"]}["precipitation"] == "accuracy"
    assert {v["id"]: v["unit"] for v in body["variables"]}["wind"] == "m/s"
    assert [p["id"] for p in body["periods"]] == ["30d", "90d", "12m"]
    assert body["status"]["latest_scored_day"] == "2026-09-30"


def test_meta_carries_the_attribution_word_for_word(client: TestClient) -> None:
    given = client.get("/api/meta").json()["attribution"]
    assert given["imgw_source"] == attribution.IMGW_SOURCE
    assert given["imgw_processed"] == attribution.IMGW_PROCESSED
    assert given["open_meteo"] == "Weather data by Open-Meteo.com"


def test_the_verdict_names_a_model_and_ranks_them(client: TestClient) -> None:
    body = client.get(
        "/api/stations/12566/verdict", params={"variable": "temperature", "period": "30d"}
    ).json()
    assert body["best_model"] == "ecmwf"
    assert body["best_model_label"] == "ECMWF"
    assert body["trust_days"] == 4
    assert body["scored_days"] == 30
    assert body["window"] == {"start": "2026-09-01", "end": "2026-09-30"}
    assert [(r["model"], r["rank"]) for r in body["ranking"]] == [("ecmwf", 1), ("icon", 2)]
    assert body["ranking"][0]["mae"] == pytest.approx(1.0)
    assert body["next_day"]["n"] == 30
    assert (body["lead_from"], body["lead_to"]) == (1, 3)


def test_a_station_without_scores_gets_an_empty_but_valid_verdict(client: TestClient) -> None:
    body = client.get(
        "/api/stations/12580/verdict", params={"variable": "temperature", "period": "30d"}
    ).json()
    assert body["best_model"] is None
    assert body["trust_days"] is None
    assert body["ranking"] == []


def test_an_unknown_station_is_a_404(client: TestClient) -> None:
    response = client.get(
        "/api/stations/99999/verdict", params={"variable": "temperature", "period": "30d"}
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "params",
    [
        {"variable": "humidity", "period": "30d"},
        {"variable": "temperature", "period": "7d"},
        {"period": "30d"},
    ],
)
def test_invalid_or_missing_parameters_are_rejected(
    client: TestClient, params: dict[str, str]
) -> None:
    assert client.get("/api/stations/12566/verdict", params=params).status_code == 422


def test_unknown_query_parameters_are_rejected_so_the_cache_cannot_be_bypassed(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/stations/12566/verdict", params={"variable": "temperature", "period": "30d", "x": "1"}
    )
    assert response.status_code == 400
    assert "x" in response.json()["detail"]
    assert client.get("/api/meta", params={"cachebust": "1"}).status_code == 400


def test_data_endpoints_can_be_cached_by_the_cdn(client: TestClient) -> None:
    response = client.get(
        "/api/stations/12566/verdict", params={"variable": "temperature", "period": "30d"}
    )
    assert "s-maxage=3600" in response.headers["cache-control"]
    assert "s-maxage" in client.get("/api/meta").headers["cache-control"]


def test_the_horizon_has_every_model_with_its_leads_in_order(client: TestClient) -> None:
    body = client.get(
        "/api/stations/12566/horizon", params={"variable": "temperature", "period": "30d"}
    ).json()
    assert body["metric"] == "mae"
    assert body["trust_threshold"] == 2.0
    assert [m["model"] for m in body["models"]] == ["icon", "ecmwf"]
    assert [lead["lead_days"] for lead in body["models"][1]["leads"]] == [1, 2, 3, 4, 5]
    assert body["models"][1]["leads"][0]["mae"] == pytest.approx(0.5)


def test_precipitation_is_reported_as_accuracy(database: MemoryDatabase) -> None:
    seed(database, Variable.PRECIPITATION)
    app = create_app()
    serve(app, make_services(database))
    body = (
        TestClient(app)
        .get("/api/stations/12566/verdict", params={"variable": "precipitation", "period": "30d"})
        .json()
    )
    assert body["ranking"][0]["accuracy"] == 1.0
    assert body["ranking"][0]["brier"] == pytest.approx(0.1)
    assert body["next_day"]["hit_rate"] == 1.0


def test_the_comparison_lists_every_station(client: TestClient) -> None:
    body = client.get("/api/comparison", params={"variable": "temperature", "period": "30d"}).json()
    assert body["lead_days"] == 1
    rows = {row["station"]["id"]: row for row in body["rows"]}
    assert rows["12566"]["best_model"] == "ecmwf"
    assert rows["12580"]["best_model"] is None
    assert rows["12580"]["figures"] is None


def test_the_comparison_validates_the_lead(client: TestClient) -> None:
    params = {"variable": "temperature", "period": "30d", "lead_days": "9"}
    assert client.get("/api/comparison", params=params).status_code == 422


def test_the_csv_export_carries_the_attribution_and_the_figures(client: TestClient) -> None:
    response = client.get(
        "/api/stations/12566/export.csv", params={"variable": "temperature", "period": "30d"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert (
        'filename="forecheck-12566-temperature-30d.csv"' in response.headers["content-disposition"]
    )

    lines = response.text.splitlines()
    comments = [line for line in lines if line.startswith("# ")]
    assert attribution.IMGW_SOURCE in comments[1]
    assert attribution.IMGW_PROCESSED in comments[2]
    rows = list(
        csv.DictReader(io.StringIO("\n".join(line for line in lines if not line.startswith("#"))))
    )
    assert len(rows) == 2 * 5
    assert rows[0]["model"] == "ecmwf"
    assert rows[0]["lead_days"] == "1"
    assert rows[0]["unit"] == "°C"
    assert float(rows[0]["mae"]) == pytest.approx(0.5)


def test_the_csv_export_of_an_unknown_station_is_a_404(client: TestClient) -> None:
    response = client.get(
        "/api/stations/00000/export.csv", params={"variable": "temperature", "period": "30d"}
    )
    assert response.status_code == 404


def test_the_cron_route_is_off_without_a_secret(database: MemoryDatabase) -> None:
    app = create_app()
    serve(app, make_services(database, cron_secret=""))
    response = TestClient(app).get("/api/cron/collect", headers={"Authorization": "Bearer "})
    assert response.status_code == 404


def test_the_cron_route_checks_the_secret_before_building_any_services() -> None:
    # No get_services override: building them here would raise (no DATABASE_URL) and answer 500.
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(cron_secret="", _env_file=None)
    response = TestClient(app).get("/api/cron/collect")
    assert response.status_code == 404

    app.dependency_overrides[get_settings] = lambda: Settings(cron_secret="s3cret", _env_file=None)
    assert TestClient(app).get("/api/cron/collect").status_code == 401


@pytest.mark.parametrize("header", [None, "Bearer wrong", "s3cret", "Basic s3cret"])
def test_the_cron_route_rejects_a_wrong_secret(client: TestClient, header: str | None) -> None:
    headers = {} if header is None else {"Authorization": header}
    assert client.get("/api/cron/collect", headers=headers).status_code == 401


def test_the_cron_route_runs_the_cycle(client: TestClient) -> None:
    response = client.get("/api/cron/collect", headers={"Authorization": "Bearer s3cret"})
    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is True
    assert [s["name"] for s in body["steps"]] == ["collect", "ingest", "evaluate"]
    assert "cache-control" not in response.headers


def test_a_cycle_that_hit_a_rate_limit_answers_502_so_the_scheduler_sees_it(
    database: MemoryDatabase,
) -> None:
    app = create_app()
    serve(app, make_services(database, rate_limited=True))
    response = TestClient(app).get("/api/cron/collect", headers={"Authorization": "Bearer s3cret"})
    assert response.status_code == 502
    assert response.json()["ok"] is False


def test_the_openapi_document_describes_the_public_api_and_hides_the_cron_route(
    client: TestClient,
) -> None:
    document = client.get("/api/openapi.json").json()
    assert set(document["paths"]) == {
        "/api/health",
        "/api/meta",
        "/api/stations/{station_id}/verdict",
        "/api/stations/{station_id}/horizon",
        "/api/comparison",
        "/api/stations/{station_id}/export.csv",
    }
    assert (
        document["paths"]["/api/stations/{station_id}/verdict"]["get"]["operationId"] == "verdict"
    )


def test_rules_and_stations_used_in_these_tests() -> None:
    assert Rules(min_samples=2) == RULES
    assert KRAKOW.id == StationId("12566")
