from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

import pytest

from forecheck.application.catalog import Catalog
from forecheck.application.errors import SourceUnavailableError
from forecheck.application.ports import UnitOfWorkFactory
from forecheck.application.use_cases.collect_forecasts import CollectForecasts
from forecheck.application.use_cases.evaluate_forecasts import EvaluateForecasts
from forecheck.application.use_cases.ingest_observations import IngestObservations
from forecheck.domain.entities import Forecast, Observation, ScoreRecord, Station
from forecheck.domain.rules import Rules
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import ModelId, StationId, Variable
from tests.support.memory import MemoryDatabase
from tests.unit.application.fakes import (
    FakeClock,
    FakeForecastSource,
    FakeObservationSource,
    clock_at,
)

STATIONS = (
    Station(StationId("12566"), "Kraków", 50.0, 19.8),
    Station(StationId("12580"), "Rzeszów", 50.1, 22.0),
    Station(StationId("12375"), "Warszawa", 52.2, 21.0),
)
CATALOG = Catalog(stations=STATIONS, models=())


@pytest.fixture
def database() -> MemoryDatabase:
    return MemoryDatabase()


def forecast_count(factory: UnitOfWorkFactory) -> int:
    with factory() as uow:
        return uow.forecasts.count()


# --- collect ---------------------------------------------------------------------------


def test_every_station_is_collected_and_stamped_with_the_run_time(database: MemoryDatabase) -> None:
    clock = clock_at(2026, 9, 10)
    source = FakeForecastSource()
    report = CollectForecasts(source, database.unit_of_work, clock, CATALOG).run()

    assert report.ok
    assert report.stored == 3 * 3 * 7  # stations x models x leads
    with database.unit_of_work() as uow:
        stored = uow.forecasts.pending(date(2026, 9, 30))
    assert {f.issued_at for f in stored} == {clock.now()}
    assert {f.lead_days for f in stored} == set(range(1, 8))


def test_collecting_twice_on_one_day_does_not_duplicate(database: MemoryDatabase) -> None:
    collect = CollectForecasts(
        FakeForecastSource(), database.unit_of_work, clock_at(2026, 9, 10), CATALOG
    )
    collect.run()
    collect.run()
    assert forecast_count(database.unit_of_work) == 3 * 3 * 7


def test_one_failing_station_does_not_stop_the_others(database: MemoryDatabase) -> None:
    source = FakeForecastSource(failing=["12580"])
    report = CollectForecasts(source, database.unit_of_work, clock_at(2026, 9, 10), CATALOG).run()

    assert not report.ok
    assert report.failed == ("12580",)
    assert not report.rate_limited
    assert report.stored == 2 * 3 * 7


def test_a_rate_limit_stops_asking_and_leaves_the_rest_for_tomorrow(
    database: MemoryDatabase,
) -> None:
    source = FakeForecastSource(rate_limited_at="12580")
    report = CollectForecasts(source, database.unit_of_work, clock_at(2026, 9, 10), CATALOG).run()

    assert report.rate_limited
    assert source.requested == ["12566", "12580"]  # Warszawa was never asked
    assert report.failed == ("12580", "12375")
    assert report.stored == 1 * 3 * 7


def test_the_provider_is_given_a_pause_between_stations(database: MemoryDatabase) -> None:
    pauses: list[int] = []
    CollectForecasts(
        FakeForecastSource(),
        database.unit_of_work,
        clock_at(2026, 9, 10),
        CATALOG,
        pause=lambda: pauses.append(1),
    ).run()
    assert len(pauses) == 2


# --- ingest ----------------------------------------------------------------------------


def seed_forecast(database: MemoryDatabase, valid: date) -> None:
    issued = datetime(valid.year, valid.month, valid.day, tzinfo=UTC)
    with database.unit_of_work() as uow:
        uow.forecasts.upsert(
            [
                Forecast(
                    STATIONS[0].id,
                    ModelId("icon"),
                    Variable.TEMPERATURE,
                    valid,
                    issued.replace(day=valid.day - 1),
                    10.0,
                )
            ]
        )
        uow.commit()


def ingest(
    database: MemoryDatabase, source: FakeObservationSource, clock: FakeClock
) -> IngestObservations:
    return IngestObservations(source, database.unit_of_work, clock, CATALOG)


def test_nothing_is_read_when_no_forecast_is_waiting(database: MemoryDatabase) -> None:
    source = FakeObservationSource({date(2026, 9, 1): "v1"})
    report = ingest(database, source, clock_at(2026, 10, 20)).run()
    assert (report.months_read, report.observations) == (0, 0)
    assert source.fetches == []


def test_nothing_is_read_for_days_that_are_not_over_yet(database: MemoryDatabase) -> None:
    seed_forecast(database, date(2026, 10, 20))
    source = FakeObservationSource({date(2026, 10, 1): "v1"})
    assert ingest(database, source, clock_at(2026, 10, 20)).run().months_read == 0


def test_the_months_between_the_oldest_waiting_forecast_and_yesterday_are_read(
    database: MemoryDatabase,
) -> None:
    seed_forecast(database, date(2026, 8, 20))
    source = FakeObservationSource(
        {date(2026, 8, 1): "a", date(2026, 9, 1): "b", date(2026, 10, 1): "c"}
    )
    report = ingest(database, source, clock_at(2026, 10, 5)).run()

    assert report.months_read == 3
    assert source.fetches == [
        (date(2026, 8, 20), date(2026, 8, 31)),
        (date(2026, 9, 1), date(2026, 9, 30)),
        (date(2026, 10, 1), date(2026, 10, 4)),
    ]
    with database.unit_of_work() as uow:
        assert uow.observations.latest_day() == date(2026, 10, 4)


def test_a_month_that_has_not_been_republished_is_not_read_again(database: MemoryDatabase) -> None:
    seed_forecast(database, date(2026, 9, 5))
    source = FakeObservationSource({date(2026, 9, 1): "v1"})
    clock = clock_at(2026, 10, 20)
    ingest(database, source, clock).run()
    assert ingest(database, source, clock).run().months_read == 0
    assert len(source.fetches) == 1


def test_a_month_read_only_in_part_is_read_again_for_the_days_it_missed(
    database: MemoryDatabase,
) -> None:
    source = FakeObservationSource({date(2026, 7, 1): "v1"})
    use_case = ingest(database, source, clock_at(2026, 10, 20))
    use_case.read_range(date(2026, 7, 15), date(2026, 7, 31))
    assert use_case.read_range(date(2026, 7, 1), date(2026, 7, 31)).months_read == 1
    assert source.fetches == [
        (date(2026, 7, 15), date(2026, 7, 31)),
        (date(2026, 7, 1), date(2026, 7, 31)),
    ]
    # Days already covered are not fetched again.
    assert use_case.read_range(date(2026, 7, 10), date(2026, 7, 20)).months_read == 0


def test_a_month_that_cannot_be_read_does_not_hold_back_the_newer_ones(
    database: MemoryDatabase,
) -> None:
    class BrokenAugust(FakeObservationSource):
        def fetch_observations(
            self, stations: Sequence[Station], start: date, end: date
        ) -> list[Observation]:
            if start.month == 8:
                raise SourceUnavailableError("corrupt archive")
            return super().fetch_observations(stations, start, end)

    seed_forecast(database, date(2026, 8, 20))
    source = BrokenAugust({date(2026, 8, 1): "a", date(2026, 9, 1): "b"})
    use_case = ingest(database, source, clock_at(2026, 10, 5))

    report = use_case.run()
    assert (report.months_read, report.failed) == (1, (date(2026, 8, 1),))
    with database.unit_of_work() as uow:
        assert uow.observations.latest_day() == date(2026, 9, 30)

    # Nothing was recorded for August, so it is tried again.
    assert use_case.run().failed == (date(2026, 8, 1),)


def test_a_republished_month_is_read_again(database: MemoryDatabase) -> None:
    seed_forecast(database, date(2026, 9, 5))
    source = FakeObservationSource({date(2026, 9, 1): "v1"})
    clock = clock_at(2026, 10, 20)
    ingest(database, source, clock).run()
    source.months[date(2026, 9, 1)] = "v2"
    assert ingest(database, source, clock).run().months_read == 1


def test_the_arrival_of_the_next_month_completes_the_last_day_of_the_previous_one(
    database: MemoryDatabase,
) -> None:
    # Precipitation of 30 September needs the 00 UTC report of 1 October: read September again.
    seed_forecast(database, date(2026, 9, 5))
    source = FakeObservationSource({date(2026, 9, 1): "v1"})
    clock = clock_at(2026, 10, 20)
    ingest(database, source, clock).run()
    source.months[date(2026, 10, 1)] = "v1"
    report = ingest(database, source, clock).run()
    assert report.months_read == 2  # September again, and October for the first time


# --- evaluate --------------------------------------------------------------------------


def evaluate(
    database: MemoryDatabase,
    clock: FakeClock,
    rules: Rules | None = None,
    max_pending_days: int = 90,
) -> EvaluateForecasts:
    return EvaluateForecasts(database.unit_of_work, clock, rules or Rules(), max_pending_days)


def store(
    database: MemoryDatabase, forecasts: list[Forecast], observations: list[Observation]
) -> None:
    with database.unit_of_work() as uow:
        uow.forecasts.upsert(forecasts)
        uow.observations.upsert(observations)
        uow.commit()


def make_forecast(
    day: date, lead: int, value: float, variable: Variable = Variable.TEMPERATURE
) -> Forecast:
    issued = datetime(day.year, day.month, day.day, 9, 0, tzinfo=UTC).replace()
    return Forecast(
        STATIONS[0].id, ModelId("icon"), variable, day, issued - timedelta(days=lead), value
    )


def test_a_forecast_meeting_its_measurement_is_scored_and_removed(database: MemoryDatabase) -> None:
    day = date(2026, 9, 10)
    store(
        database,
        [make_forecast(day, 1, 12.0), make_forecast(day, 2, 9.0)],
        [Observation(STATIONS[0].id, Variable.TEMPERATURE, day, 10.0)],
    )
    report = evaluate(database, clock_at(2026, 10, 1)).run()

    assert (report.scored, report.waiting) == (2, 0)
    with database.unit_of_work() as uow:
        totals = uow.scores.by_lead(STATIONS[0].id, Variable.TEMPERATURE, day, day)[ModelId("icon")]
    assert totals[1].mae == 2.0
    assert totals[1].bias == 2.0
    assert totals[2].bias == -1.0


def test_a_forecast_without_a_measurement_keeps_waiting(database: MemoryDatabase) -> None:
    store(
        database,
        [make_forecast(date(2026, 9, 10), 1, 12.0), make_forecast(date(2026, 9, 12), 1, 12.0)],
        [Observation(STATIONS[0].id, Variable.TEMPERATURE, date(2026, 9, 10), 10.0)],
    )
    report = evaluate(database, clock_at(2026, 10, 1)).run()
    assert (report.scored, report.waiting) == (1, 1)


def test_a_measurement_of_another_variable_does_not_score_a_forecast(
    database: MemoryDatabase,
) -> None:
    day = date(2026, 9, 10)
    store(
        database,
        [make_forecast(day, 1, 12.0)],
        [Observation(STATIONS[0].id, Variable.WIND, day, 3.0)],
    )
    assert evaluate(database, clock_at(2026, 10, 1)).run().scored == 0


def test_a_forecast_that_can_never_be_scored_is_dropped_after_a_while(
    database: MemoryDatabase,
) -> None:
    store(
        database,
        [make_forecast(date(2026, 5, 1), 1, 12.0)],
        [Observation(STATIONS[0].id, Variable.WIND, date(2026, 9, 1), 3.0)],
    )
    report = evaluate(database, clock_at(2026, 10, 1), max_pending_days=90).run()
    assert (report.scored, report.expired, report.waiting) == (0, 1, 0)


def test_precipitation_uses_the_wet_threshold_of_the_rules(database: MemoryDatabase) -> None:
    day = date(2026, 9, 10)
    store(
        database,
        [make_forecast(day, 1, 0.5, Variable.PRECIPITATION)],
        [Observation(STATIONS[0].id, Variable.PRECIPITATION, day, 0.5)],
    )
    evaluate(database, clock_at(2026, 10, 1), Rules(precipitation_threshold_mm=1.0)).run()
    with database.unit_of_work() as uow:
        stats = uow.scores.by_lead(STATIONS[0].id, Variable.PRECIPITATION, day, day)[
            ModelId("icon")
        ][1]
    assert (stats.hits, stats.correct_negatives) == (0, 1)


def test_evaluating_again_changes_nothing(database: MemoryDatabase) -> None:
    day = date(2026, 9, 10)
    store(
        database,
        [make_forecast(day, 1, 12.0)],
        [Observation(STATIONS[0].id, Variable.TEMPERATURE, day, 10.0)],
    )
    evaluate(database, clock_at(2026, 10, 1)).run()
    second = evaluate(database, clock_at(2026, 10, 1)).run()
    assert second.scored == 0
    with database.unit_of_work() as uow:
        assert (
            uow.scores.by_lead(STATIONS[0].id, Variable.TEMPERATURE, day, day)[ModelId("icon")][1].n
            == 1
        )


def test_with_no_measurements_nothing_happens(database: MemoryDatabase) -> None:
    store(database, [make_forecast(date(2026, 9, 10), 1, 12.0)], [])
    report = evaluate(database, clock_at(2026, 10, 1)).run()
    assert (report.scored, report.waiting) == (0, 1)


# --- keeping the scores table from growing without end -----------------------------------


def seed_score(database: MemoryDatabase, *days: date) -> None:
    stats = ErrorStats(n=1, abs_error_sum=1.0)
    with database.unit_of_work() as uow:
        uow.scores.upsert(
            [
                ScoreRecord(STATIONS[0].id, ModelId("icon"), Variable.TEMPERATURE, 1, day, stats)
                for day in days
            ]
        )
        uow.commit()


def kept_days(database: MemoryDatabase, *days: date) -> set[date]:
    """Which of ``days`` still have a score."""
    with database.unit_of_work() as uow:
        return {
            day
            for day in days
            if uow.scores.by_lead(STATIONS[0].id, Variable.TEMPERATURE, day, day)
        }


def test_scores_older_than_the_retention_are_dropped_counting_back_from_the_latest(
    database: MemoryDatabase,
) -> None:
    # 730 days before 2026-09-30 is 2024-09-30: the day before it goes, the boundary day stays.
    seed_score(database, date(2024, 9, 29), date(2024, 9, 30), date(2026, 9, 30))
    report = evaluate(database, clock_at(2026, 10, 20)).run()
    assert report.pruned == 1
    days = (date(2024, 9, 29), date(2024, 9, 30), date(2026, 9, 30))
    assert kept_days(database, *days) == {date(2024, 9, 30), date(2026, 9, 30)}


def test_the_retention_is_counted_from_the_latest_score_not_from_today(
    database: MemoryDatabase,
) -> None:
    # Scoring has stalled for years: what the page still shows must not be deleted.
    seed_score(database, date(2026, 9, 1), date(2026, 9, 30))
    report = evaluate(database, clock_at(2030, 1, 1)).run()
    assert report.pruned == 0
    assert kept_days(database, date(2026, 9, 1), date(2026, 9, 30)) == {
        date(2026, 9, 1),
        date(2026, 9, 30),
    }
