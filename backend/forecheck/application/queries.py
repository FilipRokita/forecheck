"""The read side: what the API shows, built from the stored scores."""

from dataclasses import dataclass
from datetime import date, timedelta

from forecheck.application.catalog import Catalog, ModelSpec
from forecheck.application.ports import RunRecord, UnitOfWorkFactory
from forecheck.domain.entities import Station
from forecheck.domain.ranking import RankedModel, rank_models
from forecheck.domain.rules import Rules
from forecheck.domain.stats import ErrorStats
from forecheck.domain.types import (
    MAX_LEAD_DAYS,
    MIN_LEAD_DAYS,
    ModelId,
    Period,
    StationId,
    Variable,
)
from forecheck.domain.verdict import Verdict, build_verdict

# The key under which a demo seed marks the data it wrote.
SAMPLE_DATA_KEY = "sample_data"


class UnknownStationError(LookupError):
    """The station id is not in the catalog."""


@dataclass(frozen=True, slots=True)
class Window:
    """The scored days a figure is summed over. ``None`` when nothing has been scored yet."""

    start: date
    end: date


@dataclass(frozen=True, slots=True)
class VerdictView:
    station: Station
    variable: Variable
    period: Period
    window: Window | None
    verdict: Verdict
    # Days of day-ahead forecasts behind the best model's figures: how much history there is.
    scored_days: int
    rules: Rules


@dataclass(frozen=True, slots=True)
class HorizonView:
    station: Station
    variable: Variable
    period: Period
    window: Window | None
    # Per model, per lead 1..7. Missing leads have no scored days.
    stats: dict[ModelId, dict[int, ErrorStats]]
    rules: Rules


@dataclass(frozen=True, slots=True)
class StationRow:
    station: Station
    best: RankedModel | None


@dataclass(frozen=True, slots=True)
class ComparisonView:
    variable: Variable
    period: Period
    lead: int
    window: Window | None
    rows: list[StationRow]


@dataclass(frozen=True, slots=True)
class StatusView:
    # True while the scores are made-up demo data (scripts/seed_demo.py), never on a real host.
    sample_data: bool
    latest_scored_day: date | None
    waiting_forecasts: int
    last_runs: dict[str, RunRecord]


@dataclass(frozen=True, slots=True)
class ExportRow:
    model: ModelId
    lead_days: int
    stats: ErrorStats


class Reports:
    def __init__(self, uow_factory: UnitOfWorkFactory, catalog: Catalog, rules: Rules) -> None:
        self._uow_factory = uow_factory
        self._catalog = catalog
        self._rules = rules

    @property
    def catalog(self) -> Catalog:
        return self._catalog

    @property
    def rules(self) -> Rules:
        return self._rules

    def models(self) -> list[ModelSpec]:
        return list(self._catalog.models)

    def status(self) -> StatusView:
        with self._uow_factory() as uow:
            return StatusView(
                sample_data=uow.state.get(SAMPLE_DATA_KEY) == "1",
                latest_scored_day=uow.scores.latest_day(),
                waiting_forecasts=uow.forecasts.count(),
                last_runs={
                    run.kind: run
                    for kind in ("collect", "ingest", "evaluate")
                    if (run := uow.runs.latest(kind)) is not None
                },
            )

    def verdict(self, station_id: StationId, variable: Variable, period: Period) -> VerdictView:
        station = self._station(station_id)
        window, per_lead = self._per_lead(station, variable, period)
        verdict = build_verdict(variable, per_lead, self._rules)
        scored_days = 0
        if verdict.best is not None:
            first = per_lead[verdict.best].get(MIN_LEAD_DAYS)
            scored_days = first.n if first else 0
        return VerdictView(station, variable, period, window, verdict, scored_days, self._rules)

    def horizon(self, station_id: StationId, variable: Variable, period: Period) -> HorizonView:
        station = self._station(station_id)
        window, per_lead = self._per_lead(station, variable, period)
        return HorizonView(station, variable, period, window, per_lead, self._rules)

    def comparison(
        self, variable: Variable, period: Period, lead: int = MIN_LEAD_DAYS
    ) -> ComparisonView:
        if not MIN_LEAD_DAYS <= lead <= MAX_LEAD_DAYS:
            raise ValueError(f"lead must be {MIN_LEAD_DAYS} to {MAX_LEAD_DAYS}")
        with self._uow_factory() as uow:
            window = self._window(uow.scores.latest_day(), period)
            by_station = (
                uow.scores.by_station(variable, lead, window.start, window.end) if window else {}
            )
        rows = []
        for station in self._catalog.stations:
            ranked = rank_models(
                variable, by_station.get(station.id, {}), min_samples=self._rules.min_samples
            )
            best = ranked[0] if ranked and ranked[0].rank == 1 else None
            rows.append(StationRow(station, best))
        return ComparisonView(variable, period, lead, window, rows)

    def export_rows(
        self, station_id: StationId, variable: Variable, period: Period
    ) -> list[ExportRow]:
        _, per_lead = self._per_lead(self._station(station_id), variable, period)
        return [
            ExportRow(model, lead, stats)
            for model in sorted(per_lead)
            for lead, stats in sorted(per_lead[model].items())
        ]

    # --- helpers -----------------------------------------------------------------------

    def _station(self, station_id: StationId) -> Station:
        station = self._catalog.station(station_id)
        if station is None:
            raise UnknownStationError(station_id)
        return station

    @staticmethod
    def _window(latest: date | None, period: Period) -> Window | None:
        if latest is None:
            return None
        return Window(start=latest - timedelta(days=period.days - 1), end=latest)

    def _per_lead(
        self, station: Station, variable: Variable, period: Period
    ) -> tuple[Window | None, dict[ModelId, dict[int, ErrorStats]]]:
        with self._uow_factory() as uow:
            window = self._window(uow.scores.latest_day(), period)
            if window is None:
                return None, {}
            return window, uow.scores.by_lead(station.id, variable, window.start, window.end)
