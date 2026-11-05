from datetime import UTC, date, datetime, timedelta

import pytest

from forecheck.application.catalog import Catalog, ModelSpec
from forecheck.application.errors import SourceUnavailableError
from forecheck.application.ports import RunRecord
from forecheck.application.queries import Reports, UnknownStationError
from forecheck.application.use_cases.backfill_scores import BackfillScores
from forecheck.application.use_cases.collect_forecasts import CollectForecasts
from forecheck.application.use_cases.evaluate_forecasts import EvaluateForecasts
from forecheck.application.use_cases.ingest_observations import IngestObservations
from forecheck.application.use_cases.run_daily_cycle import RunDailyCycle
from forecheck.domain.entities import Forecast, Observation, ScoreRecord, Station
from forecheck.domain.rules import Rules
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import ModelId, Period, StationId, Variable
from tests.support.memory import MemoryDatabase, MemoryRuns
from tests.unit.application.fakes import (
    FakeArchive,
    FakeClock,
    FakeForecastSource,
    FakeObservationSource,
    clock_at,
)

KRAKOW = Station(StationId("12566"), "Kraków", 50.0, 19.8)
RZESZOW = Station(StationId("12580"), "Rzeszów", 50.1, 22.0)
CATALOG = Catalog(
    stations=(KRAKOW, RZESZOW),
    models=(
        ModelSpec(ModelId("icon"), "ICON", "icon_seamless"),
        ModelSpec(ModelId("ecmwf"), "ECMWF", "ecmwf_ifs025"),
    ),
)
RULES = Rules(min_samples=2)


def cycle(
    database: MemoryDatabase,
    clock: FakeClock,
    forecasts: FakeForecastSource,
    observations: FakeObservationSource,
) -> RunDailyCycle:
    return RunDailyCycle(
        CollectForecasts(forecasts, database.unit_of_work, clock, CATALOG),
        IngestObservations(observations, database.unit_of_work, clock, CATALOG),
        EvaluateForecasts(database.unit_of_work, clock, RULES),
        database.unit_of_work,
        clock,
    )


# --- the daily cycle -----------------------------------------------------------------------


def test_a_week_of_cycles_collects_reads_and_scores() -> None:
    """The whole pipeline: forecasts on day 1 are scored once IMGW publishes the month."""
    database = MemoryDatabase()
    clock = clock_at(2026, 9, 1)
    forecasts = FakeForecastSource(value=10.0, models=("icon", "ecmwf"))
    observations = FakeObservationSource({}, value=11.0)
    job = cycle(database, clock, forecasts, observations)

    for _ in range(10):  # 1 to 10 September: nothing is published yet
        assert job.run().ok
        clock.advance(1)
    with database.unit_of_work() as uow:
        assert uow.scores.latest_day() is None
        assert uow.forecasts.count() > 0

    observations.months[date(2026, 9, 1)] = "published"  # IMGW publishes September
    clock.advance(30)  # it is now 10 October
    report = job.run()
    assert report.ok

    with database.unit_of_work() as uow:
        latest = uow.scores.latest_day()
        assert latest is not None
        totals = uow.scores.by_lead(KRAKOW.id, Variable.TEMPERATURE, date(2026, 9, 1), latest)
    icon = ModelId("icon")
    assert set(totals) == {icon, ModelId("ecmwf")}
    assert totals[icon][1].bias == -1.0  # forecast 10, measured 11
    assert totals[icon][1].mae == 1.0
    assert set(totals[icon]) == set(range(1, 8))


def test_every_step_is_logged_with_the_time_it_ran() -> None:
    database = MemoryDatabase()
    clock = clock_at(2026, 9, 1)
    cycle(database, clock, FakeForecastSource(), FakeObservationSource({})).run()
    with database.unit_of_work() as uow:
        runs = {kind: uow.runs.latest(kind) for kind in ("collect", "ingest", "evaluate")}
    assert all(run is not None and run.ok and run.at == clock.now() for run in runs.values())
    assert runs["collect"] is not None
    assert "stored" in runs["collect"].message


def test_a_failing_step_is_reported_and_the_others_still_run() -> None:
    database = MemoryDatabase()
    clock = clock_at(2026, 9, 1)

    class Broken:
        def available_months(self, *_: object) -> dict[date, str]:
            raise SourceUnavailableError("IMGW is down")

        def fetch_observations(self, *_: object) -> list[Observation]:
            raise AssertionError("not reached")

    with database.unit_of_work() as uow:  # a waiting forecast, so ingest has something to do
        uow.forecasts.upsert([
            Forecast(KRAKOW.id, ModelId("icon"), Variable.TEMPERATURE, date(2026, 8, 20),
                     datetime(2026, 8, 19, tzinfo=UTC), 10.0)
        ])  # fmt: skip
        uow.commit()
    job = RunDailyCycle(
        CollectForecasts(FakeForecastSource(), database.unit_of_work, clock, CATALOG),
        IngestObservations(Broken(), database.unit_of_work, clock, CATALOG),
        EvaluateForecasts(database.unit_of_work, clock, RULES),
        database.unit_of_work,
        clock,
    )
    report = job.run()

    assert not report.ok
    assert [(s.name, s.ok) for s in report.steps] == [
        ("collect", True),
        ("ingest", False),
        ("evaluate", True),
    ]
    assert "IMGW is down" in report.steps[1].message
    with database.unit_of_work() as uow:
        latest = uow.runs.latest("ingest")
        assert latest is not None
        assert not latest.ok


def test_a_failure_to_log_a_step_does_not_stop_the_next_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = MemoryDatabase()
    clock = clock_at(2026, 9, 1)
    real_record = MemoryRuns.record
    calls: list[str] = []

    def flaky(self: MemoryRuns, run: RunRecord) -> None:
        calls.append(run.kind)
        if run.kind == "collect":
            raise OSError("connection reset")
        real_record(self, run)

    monkeypatch.setattr(MemoryRuns, "record", flaky)
    report = cycle(database, clock, FakeForecastSource(), FakeObservationSource({})).run()

    assert [(s.name, s.ok) for s in report.steps] == [
        ("collect", True),
        ("ingest", True),
        ("evaluate", True),
    ]
    assert calls == ["collect", "ingest", "evaluate"]


def test_a_month_that_could_not_be_read_makes_the_ingest_step_fail_and_names_it() -> None:
    class BrokenAugust(FakeObservationSource):
        def fetch_observations(self, stations: object, start: date, end: date) -> list[Observation]:
            if start.month == 8:
                raise SourceUnavailableError("corrupt archive")
            return super().fetch_observations(stations, start, end)  # type: ignore[arg-type]

    database = MemoryDatabase()
    with database.unit_of_work() as uow:
        uow.forecasts.upsert([
            Forecast(KRAKOW.id, ModelId("icon"), Variable.TEMPERATURE, date(2026, 8, 20),
                     datetime(2026, 8, 19, tzinfo=UTC), 10.0)
        ])  # fmt: skip
        uow.commit()
    source = BrokenAugust({date(2026, 8, 1): "a", date(2026, 9, 1): "b"})
    report = cycle(database, clock_at(2026, 10, 5), FakeForecastSource(), source).run()

    ingest_step = next(step for step in report.steps if step.name == "ingest")
    assert not ingest_step.ok
    assert "2026-08" in ingest_step.message


def test_a_rate_limited_collection_makes_the_cycle_not_ok_but_says_why() -> None:
    database = MemoryDatabase()
    source = FakeForecastSource(rate_limited_at=KRAKOW.id)
    report = cycle(database, clock_at(2026, 9, 1), source, FakeObservationSource({})).run()
    assert not report.ok
    assert "rate limiting" in report.steps[0].message


# --- backfill ------------------------------------------------------------------------------


def backfill(
    database: MemoryDatabase, archive: FakeArchive, observations: FakeObservationSource
) -> BackfillScores:
    clock = clock_at(2026, 10, 20)
    return BackfillScores(
        archive,
        IngestObservations(observations, database.unit_of_work, clock, CATALOG),
        database.unit_of_work,
        CATALOG,
        RULES,
    )


def test_backfill_scores_archived_forecasts_against_measurements() -> None:
    database = MemoryDatabase()
    observations = FakeObservationSource({date(2026, 9, 1): "v1"}, value=11.0)
    report = backfill(database, FakeArchive(value=10.0), observations).run(
        date(2026, 9, 1), date(2026, 9, 5)
    )

    assert report.scored == 2 * 5 * 2 * 7  # stations x days x models x leads
    with database.unit_of_work() as uow:
        totals = uow.scores.by_lead(
            KRAKOW.id, Variable.TEMPERATURE, date(2026, 9, 1), date(2026, 9, 5)
        )
        assert totals[ModelId("icon")][3].n == 5
        assert totals[ModelId("icon")][3].mae == 1.0
        assert uow.forecasts.count() == 0  # nothing is left waiting


def test_backfill_can_be_repeated_and_limited_to_some_stations() -> None:
    database = MemoryDatabase()
    observations = FakeObservationSource({date(2026, 9, 1): "v1"})
    archive = FakeArchive()
    job = backfill(database, archive, observations)
    job.run(date(2026, 9, 1), date(2026, 9, 2), only=[RZESZOW.id])
    job.run(date(2026, 9, 1), date(2026, 9, 2), only=[RZESZOW.id])

    assert archive.calls == [RZESZOW.id, RZESZOW.id]
    with database.unit_of_work() as uow:
        assert (
            uow.scores.by_lead(KRAKOW.id, Variable.TEMPERATURE, date(2026, 9, 1), date(2026, 9, 2))
            == {}
        )
        totals = uow.scores.by_lead(
            RZESZOW.id, Variable.TEMPERATURE, date(2026, 9, 1), date(2026, 9, 2)
        )
        assert totals[ModelId("icon")][1].n == 2  # not 4: the second run replaced the first


def test_backfill_does_not_replace_a_score_made_from_a_live_forecast() -> None:
    database = MemoryDatabase()
    day = date(2026, 9, 1)
    live = ErrorStats(n=1, abs_error_sum=4.0, error_sum=4.0, squared_error_sum=16.0)
    with database.unit_of_work() as uow:
        uow.scores.upsert(
            [ScoreRecord(KRAKOW.id, ModelId("icon"), Variable.TEMPERATURE, 1, day, live)]
        )
        uow.commit()

    observations = FakeObservationSource({date(2026, 9, 1): "v1"}, value=11.0)
    backfill(database, FakeArchive(value=10.0), observations).run(day, day, only=[KRAKOW.id])

    with database.unit_of_work() as uow:
        totals = uow.scores.by_lead(KRAKOW.id, Variable.TEMPERATURE, day, day)
        assert totals[ModelId("icon")][1] == live
        assert totals[ModelId("icon")][2].n == 1  # leads that were missing are filled in


def test_backfill_skips_forecasts_without_a_measurement() -> None:
    database = MemoryDatabase()
    report = backfill(database, FakeArchive(), FakeObservationSource({})).run(
        date(2026, 9, 1), date(2026, 9, 2)
    )
    assert report.scored == 0


# --- reports -------------------------------------------------------------------------------


def seed_scores(
    database: MemoryDatabase, errors: dict[tuple[str, str], float], days: int = 30
) -> date:
    """Score ``days`` days per (station, model), with the given error at leads 1 to 5."""
    last = date(2026, 9, 30)
    records = []
    for (station, model), error in errors.items():
        for offset in range(days):
            for lead in range(1, 6):
                stats = ErrorStats(
                    n=1,
                    abs_error_sum=error * lead / 2,
                    error_sum=error * lead / 2,
                    squared_error_sum=error**2,
                )
                records.append(
                    ScoreRecord(
                        StationId(station), ModelId(model), Variable.TEMPERATURE, lead,
                        last - timedelta(days=offset), stats,
                    )
                )  # fmt: skip
    with database.unit_of_work() as uow:
        uow.scores.upsert(records)
        uow.commit()
    return last


def reports(database: MemoryDatabase) -> Reports:
    return Reports(database.unit_of_work, CATALOG, RULES)


def test_the_verdict_names_the_best_model_and_how_far_to_trust_it() -> None:
    database = MemoryDatabase()
    last = seed_scores(database, {("12566", "icon"): 1.2, ("12566", "ecmwf"): 1.0})
    view = reports(database).verdict(KRAKOW.id, Variable.TEMPERATURE, Period.DAYS_30)

    assert view.verdict.best == "ecmwf"
    assert view.window is not None
    assert (view.window.start, view.window.end) == (last - timedelta(days=29), last)
    assert view.scored_days == 30
    assert (
        view.verdict.trust_days == 4
    )  # MAE at lead N is 0.5 * N here: 2.0 at lead 4, 2.5 at lead 5


def test_a_longer_period_sees_more_days() -> None:
    database = MemoryDatabase()
    seed_scores(database, {("12566", "ecmwf"): 1.0}, days=100)
    month = reports(database).verdict(KRAKOW.id, Variable.TEMPERATURE, Period.DAYS_30)
    quarter = reports(database).verdict(KRAKOW.id, Variable.TEMPERATURE, Period.DAYS_90)
    assert (month.scored_days, quarter.scored_days) == (30, 90)


def test_before_anything_is_scored_the_verdict_is_empty_not_an_error() -> None:
    view = reports(MemoryDatabase()).verdict(KRAKOW.id, Variable.TEMPERATURE, Period.DAYS_30)
    assert view.window is None
    assert view.verdict.best is None
    assert view.verdict.ranking == []


def test_an_unknown_station_is_reported() -> None:
    with pytest.raises(UnknownStationError):
        reports(MemoryDatabase()).verdict(StationId("00000"), Variable.TEMPERATURE, Period.DAYS_30)


def test_the_comparison_lists_every_station_with_its_best_model() -> None:
    database = MemoryDatabase()
    seed_scores(
        database, {("12566", "icon"): 1.0, ("12566", "ecmwf"): 1.4, ("12580", "ecmwf"): 0.8}
    )
    view = reports(database).comparison(Variable.TEMPERATURE, Period.DAYS_30)

    best = {row.station.id: row.best.model if row.best else None for row in view.rows}
    assert best == {KRAKOW.id: "icon", RZESZOW.id: "ecmwf"}
    assert view.lead == 1


def test_a_station_without_enough_scored_days_has_no_best_model() -> None:
    database = MemoryDatabase()
    seed_scores(database, {("12566", "icon"): 1.0}, days=30)
    seed_scores(database, {("12580", "icon"): 1.0}, days=1)
    rows = {
        row.station.id: row.best
        for row in reports(database).comparison(Variable.TEMPERATURE, Period.DAYS_30).rows
    }
    assert rows[KRAKOW.id] is not None
    assert rows[RZESZOW.id] is None


def test_the_comparison_rejects_a_lead_outside_one_to_seven() -> None:
    with pytest.raises(ValueError, match="lead"):
        reports(MemoryDatabase()).comparison(Variable.TEMPERATURE, Period.DAYS_30, lead=9)


def test_the_export_is_ordered_by_model_then_lead() -> None:
    database = MemoryDatabase()
    seed_scores(database, {("12566", "icon"): 1.0, ("12566", "ecmwf"): 1.4})
    rows = reports(database).export_rows(KRAKOW.id, Variable.TEMPERATURE, Period.DAYS_30)
    assert [(r.model, r.lead_days) for r in rows][:2] == [("ecmwf", 1), ("ecmwf", 2)]
    assert len(rows) == 2 * 5


def test_the_status_reports_freshness() -> None:
    database = MemoryDatabase()
    last = seed_scores(database, {("12566", "icon"): 1.0}, days=3)
    clock = clock_at(2026, 10, 20)
    cycle(database, clock, FakeForecastSource(), FakeObservationSource({})).run()
    status = reports(database).status()

    assert status.latest_scored_day == last
    assert set(status.last_runs) == {"collect", "ingest", "evaluate"}
    assert status.waiting_forecasts > 0
