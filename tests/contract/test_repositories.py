"""What every implementation of the repository ports must do."""

from datetime import UTC, date, datetime, timedelta

import pytest

from forecheck.application.ports import RunRecord, UnitOfWorkFactory
from forecheck.domain.entities import Forecast, Observation, ScoreRecord
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import ModelId, StationId, Variable

KRAKOW, RZESZOW = StationId("12566"), StationId("12580")
ICON, ECMWF = ModelId("icon"), ModelId("ecmwf")


def forecast(
    day: date,
    *,
    station: StationId = KRAKOW,
    model: ModelId = ECMWF,
    variable: Variable = Variable.TEMPERATURE,
    lead: int = 1,
    value: float = 10.0,
    probability: float | None = None,
) -> Forecast:
    issued = datetime(day.year, day.month, day.day, 9, 0, tzinfo=UTC) - timedelta(days=lead)
    return Forecast(station, model, variable, day, issued, value, probability)


def record(
    day: date, *, lead: int = 1, model: ModelId = ECMWF, station: StationId = KRAKOW, **stats: float
) -> ScoreRecord:
    figures = {"n": 1, "abs_error_sum": 1.0, "error_sum": 1.0, "squared_error_sum": 1.0, **stats}
    return ScoreRecord(station, model, Variable.TEMPERATURE, lead, day, ErrorStats(**figures))  # type: ignore[arg-type]


def test_forecasts_are_stored_and_replaced_by_key(uow_factory: UnitOfWorkFactory) -> None:
    day = date(2026, 9, 10)
    with uow_factory() as uow:
        uow.forecasts.upsert(
            [forecast(day, value=10.0, probability=0.4), forecast(day, lead=2, value=11.0)]
        )
        uow.commit()
    with uow_factory() as uow:
        uow.forecasts.upsert([forecast(day, value=12.5, probability=0.9)])
        uow.commit()
    with uow_factory() as uow:
        stored = {(f.lead_days, f.value, f.probability) for f in uow.forecasts.pending(day)}
    assert stored == {(1, 12.5, 0.9), (2, 11.0, None)}


def test_forecasts_come_back_whole(uow_factory: UnitOfWorkFactory) -> None:
    original = forecast(
        date(2026, 9, 10), variable=Variable.PRECIPITATION, value=2.5, probability=0.75
    )
    with uow_factory() as uow:
        uow.forecasts.upsert([original])
        uow.commit()
    with uow_factory() as uow:
        assert uow.forecasts.pending(date(2026, 9, 10)) == [original]


def test_pending_forecasts_stop_at_the_given_day_and_are_oldest_first(
    uow_factory: UnitOfWorkFactory,
) -> None:
    with uow_factory() as uow:
        uow.forecasts.upsert([forecast(date(2026, 9, d)) for d in (12, 10, 11)])
        uow.commit()
    with uow_factory() as uow:
        assert [f.valid_date.day for f in uow.forecasts.pending(date(2026, 9, 11))] == [10, 11]
        assert uow.forecasts.earliest_valid_date() == date(2026, 9, 10)
        assert uow.forecasts.count() == 3


def test_deleting_forecasts(uow_factory: UnitOfWorkFactory) -> None:
    keep, drop = forecast(date(2026, 9, 10), lead=1), forecast(date(2026, 9, 10), lead=2)
    with uow_factory() as uow:
        uow.forecasts.upsert([keep, drop, forecast(date(2026, 8, 1))])
        uow.forecasts.delete([drop])
        assert uow.forecasts.delete_valid_before(date(2026, 9, 1)) == 1
        uow.commit()
    with uow_factory() as uow:
        assert uow.forecasts.pending(date(2026, 12, 1)) == [keep]


def test_an_empty_store_has_no_dates(uow_factory: UnitOfWorkFactory) -> None:
    with uow_factory() as uow:
        assert uow.forecasts.earliest_valid_date() is None
        assert uow.observations.latest_day() is None
        assert uow.scores.latest_day() is None
        assert uow.state.get("missing") is None
        assert uow.runs.latest("collect") is None


def test_observations_are_stored_replaced_and_queried_by_range(
    uow_factory: UnitOfWorkFactory,
) -> None:
    def observation(day: int, value: float) -> Observation:
        return Observation(KRAKOW, Variable.WIND, date(2026, 9, day), value)

    with uow_factory() as uow:
        uow.observations.upsert([observation(1, 2.0), observation(2, 3.0), observation(3, 4.0)])
        uow.observations.upsert([observation(2, 9.0)])
        uow.commit()
    with uow_factory() as uow:
        found = uow.observations.between(date(2026, 9, 2), date(2026, 9, 3))
        assert sorted((o.day.day, o.value) for o in found) == [(2, 9.0), (3, 4.0)]
        assert uow.observations.latest_day() == date(2026, 9, 3)


def test_scores_are_summed_per_model_and_lead(uow_factory: UnitOfWorkFactory) -> None:
    with uow_factory() as uow:
        uow.scores.upsert(
            [
                record(date(2026, 9, 1), abs_error_sum=2.0),
                record(date(2026, 9, 2), abs_error_sum=4.0),
                record(date(2026, 9, 3), abs_error_sum=100.0),  # outside the window
                record(date(2026, 9, 1), lead=2, abs_error_sum=6.0),
                record(date(2026, 9, 1), model=ICON, abs_error_sum=1.0),
                record(date(2026, 9, 1), station=RZESZOW, abs_error_sum=50.0),
            ]
        )
        uow.commit()
    with uow_factory() as uow:
        totals = uow.scores.by_lead(
            KRAKOW, Variable.TEMPERATURE, date(2026, 9, 1), date(2026, 9, 2)
        )
    assert set(totals) == {ECMWF, ICON}
    assert totals[ECMWF][1].n == 2
    assert totals[ECMWF][1].abs_error_sum == 6.0
    assert totals[ECMWF][1].mae == 3.0
    assert totals[ECMWF][2].abs_error_sum == 6.0
    assert totals[ICON][1].abs_error_sum == 1.0


def test_event_counts_survive_a_round_trip(uow_factory: UnitOfWorkFactory) -> None:
    stats = ErrorStats(
        n=3,
        abs_error_sum=1.5,
        error_sum=-0.5,
        squared_error_sum=2.5,
        hits=1,
        misses=0,
        false_alarms=1,
        correct_negatives=1,
        brier_sum=0.3,
        brier_n=3,
    )
    day = date(2026, 9, 1)
    with uow_factory() as uow:
        uow.scores.upsert([ScoreRecord(KRAKOW, ECMWF, Variable.PRECIPITATION, 1, day, stats)])
        uow.commit()
    with uow_factory() as uow:
        assert uow.scores.by_lead(KRAKOW, Variable.PRECIPITATION, day, day) == {ECMWF: {1: stats}}


def test_scoring_the_same_day_again_replaces_it(uow_factory: UnitOfWorkFactory) -> None:
    day = date(2026, 9, 1)
    with uow_factory() as uow:
        uow.scores.upsert([record(day, abs_error_sum=2.0)])
        uow.scores.upsert([record(day, abs_error_sum=5.0)])
        uow.commit()
    with uow_factory() as uow:
        assert (
            uow.scores.by_lead(KRAKOW, Variable.TEMPERATURE, day, day)[ECMWF][1].abs_error_sum
            == 5.0
        )


def test_inserting_missing_scores_keeps_the_ones_that_exist(
    uow_factory: UnitOfWorkFactory,
) -> None:
    day = date(2026, 9, 1)
    with uow_factory() as uow:
        uow.scores.upsert([record(day, abs_error_sum=2.0)])
        uow.commit()
    with uow_factory() as uow:
        inserted = uow.scores.insert_missing(
            [record(day, abs_error_sum=5.0), record(day, lead=2, abs_error_sum=7.0)]
        )
        uow.commit()
    assert inserted == 1
    with uow_factory() as uow:
        totals = uow.scores.by_lead(KRAKOW, Variable.TEMPERATURE, day, day)[ECMWF]
        assert (totals[1].abs_error_sum, totals[2].abs_error_sum) == (2.0, 7.0)


def test_old_scores_can_be_deleted_by_day(uow_factory: UnitOfWorkFactory) -> None:
    with uow_factory() as uow:
        uow.scores.upsert(
            [record(date(2026, 9, 1)), record(date(2026, 9, 2)), record(date(2026, 9, 3))]
        )
        uow.commit()
    with uow_factory() as uow:
        assert uow.scores.delete_valid_before(date(2026, 9, 3)) == 2
        uow.commit()
    with uow_factory() as uow:
        assert uow.scores.latest_day() == date(2026, 9, 3)
        assert (
            uow.scores.by_lead(KRAKOW, Variable.TEMPERATURE, date(2026, 9, 1), date(2026, 9, 2))
            == {}
        )


def test_old_observations_can_be_deleted_by_day(uow_factory: UnitOfWorkFactory) -> None:
    def observation(day: int) -> Observation:
        return Observation(KRAKOW, Variable.WIND, date(2026, 9, day), 2.0)

    with uow_factory() as uow:
        uow.observations.upsert([observation(1), observation(2), observation(3)])
        uow.commit()
    with uow_factory() as uow:
        assert uow.observations.delete_before(date(2026, 9, 3)) == 2
        uow.commit()
    with uow_factory() as uow:
        found = uow.observations.between(date(2026, 9, 1), date(2026, 9, 30))
        assert [o.day.day for o in found] == [3]


def test_state_keys_can_be_deleted_by_prefix_and_bound(uow_factory: UnitOfWorkFactory) -> None:
    with uow_factory() as uow:
        for key in (
            "observations:2026-07",
            "observations:2026-08",
            "observations:2026-09",
            "other:2026-07",
        ):
            uow.state.set(key, "v")
        uow.commit()
    with uow_factory() as uow:
        assert uow.state.delete_before("observations:", "observations:2026-09") == 2
        uow.commit()
    with uow_factory() as uow:
        assert uow.state.get("observations:2026-08") is None
        assert uow.state.get("observations:2026-09") == "v"
        assert uow.state.get("other:2026-07") == "v"


def test_old_runs_can_be_deleted_by_time(uow_factory: UnitOfWorkFactory) -> None:
    old = RunRecord("collect", datetime(2026, 9, 1, 9, 0, tzinfo=UTC), True, "old")
    new = RunRecord("collect", datetime(2026, 9, 3, 9, 0, tzinfo=UTC), True, "new")
    with uow_factory() as uow:
        uow.runs.record(old)
        uow.runs.record(new)
        uow.commit()
    with uow_factory() as uow:
        assert uow.runs.delete_before(datetime(2026, 9, 2, tzinfo=UTC)) == 1
        uow.commit()
    with uow_factory() as uow:
        latest = uow.runs.latest("collect")
        assert latest is not None
        assert latest.message == "new"


def test_scores_by_station_at_one_lead(uow_factory: UnitOfWorkFactory) -> None:
    day = date(2026, 9, 1)
    with uow_factory() as uow:
        uow.scores.upsert(
            [
                record(day),
                record(day, station=RZESZOW, abs_error_sum=3.0),
                record(day, lead=2, abs_error_sum=9.0),
            ]
        )
        uow.commit()
    with uow_factory() as uow:
        by_station = uow.scores.by_station(Variable.TEMPERATURE, 1, day, day)
        assert set(by_station) == {KRAKOW, RZESZOW}
        assert by_station[RZESZOW][ECMWF].abs_error_sum == 3.0
        assert uow.scores.latest_day() == day


def test_state_is_remembered_and_replaced(uow_factory: UnitOfWorkFactory) -> None:
    with uow_factory() as uow:
        uow.state.set("observations:2026-09", "v1")
        uow.state.set("observations:2026-09", "v2")
        uow.commit()
    with uow_factory() as uow:
        assert uow.state.get("observations:2026-09") == "v2"


def test_the_latest_run_of_each_kind_is_returned(uow_factory: UnitOfWorkFactory) -> None:
    early = RunRecord("collect", datetime(2026, 9, 1, 9, 0, tzinfo=UTC), False, "boom")
    late = RunRecord("collect", datetime(2026, 9, 2, 9, 0, tzinfo=UTC), True, "stored 84")
    with uow_factory() as uow:
        uow.runs.record(late)
        uow.runs.record(early)
        uow.commit()
    with uow_factory() as uow:
        assert uow.runs.latest("collect") == late
        assert uow.runs.latest("ingest") is None


def test_leaving_without_commit_rolls_back(uow_factory: UnitOfWorkFactory) -> None:
    with uow_factory() as uow:
        uow.state.set("k", "v")
    with uow_factory() as uow:
        assert uow.state.get("k") is None


def test_an_error_inside_the_block_discards_the_work(uow_factory: UnitOfWorkFactory) -> None:
    def fail() -> None:
        with uow_factory() as uow:
            uow.state.set("k", "v")
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        fail()
    with uow_factory() as uow:
        assert uow.state.get("k") is None
