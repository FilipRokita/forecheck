"""The scheduled job: collect today's forecasts, read new measurements, score what can be scored."""

import logging
from collections.abc import Callable
from dataclasses import dataclass

from forecheck.application.ports import Clock, RunRecord, UnitOfWorkFactory
from forecheck.application.use_cases.collect_forecasts import CollectForecasts
from forecheck.application.use_cases.evaluate_forecasts import EvaluateForecasts
from forecheck.application.use_cases.ingest_observations import IngestObservations
from forecheck.application.use_cases.prune_old_data import PruneOldData

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StepResult:
    name: str
    ok: bool
    message: str


@dataclass(frozen=True, slots=True)
class CycleReport:
    steps: tuple[StepResult, ...]

    @property
    def ok(self) -> bool:
        return all(step.ok for step in self.steps)


class RunDailyCycle:
    """Runs the four steps in order. A failing step does not stop the others: collecting today's
    forecasts does not depend on reading old measurements, and scoring works on what is stored.
    Neither does a failure to log a step's result."""

    def __init__(
        self,
        collect: CollectForecasts,
        ingest: IngestObservations,
        evaluate: EvaluateForecasts,
        prune: PruneOldData,
        uow_factory: UnitOfWorkFactory,
        clock: Clock,
    ) -> None:
        self._collect = collect
        self._ingest = ingest
        self._evaluate = evaluate
        self._prune = prune
        self._uow_factory = uow_factory
        self._clock = clock

    def run(self) -> CycleReport:
        steps = (
            ("collect", self._collect_step),
            ("ingest", self._ingest_step),
            ("evaluate", self._evaluate_step),
            ("prune", self._prune_step),
        )
        results: list[StepResult] = []
        for name, step in steps:
            result = self._guarded(name, step)
            results.append(result)
            self._log(name, result)
        return CycleReport(tuple(results))

    def _log(self, name: str, result: StepResult) -> None:
        """Keep the run log. Failing to write it must not stop the steps that come after."""
        try:
            with self._uow_factory() as uow:
                uow.runs.record(RunRecord(name, self._clock.now(), result.ok, result.message))
                uow.commit()
        except Exception:  # a job must report, not crash, whatever went wrong
            log.exception("Could not record the result of step %s", name)

    @staticmethod
    def _guarded(name: str, step: Callable[[], tuple[bool, str]]) -> StepResult:
        try:
            ok, message = step()
        except Exception as error:  # a job must report, not crash, whatever went wrong
            log.exception("Step %s failed", name)
            return StepResult(name, False, f"{type(error).__name__}: {error}")
        return StepResult(name, ok, message)

    def _collect_step(self) -> tuple[bool, str]:
        report = self._collect.run()
        message = f"stored {report.stored} forecasts"
        if report.rate_limited:
            message += "; the forecast provider is rate limiting"
        elif report.failed:
            message += f"; failed stations: {', '.join(report.failed)}"
        return report.ok, message

    def _ingest_step(self) -> tuple[bool, str]:
        report = self._ingest.run()
        message = f"read {report.months_read} months, {report.observations} observations"
        if report.failed:
            months = ", ".join(f"{month:%Y-%m}" for month in report.failed)
            message += f"; could not read: {months}"
        return not report.failed, message

    def _evaluate_step(self) -> tuple[bool, str]:
        report = self._evaluate.run()
        return True, f"scored {report.scored}, expired {report.expired}, waiting {report.waiting}"

    def _prune_step(self) -> tuple[bool, str]:
        report = self._prune.run()
        return True, (
            f"dropped {report.scores} scores, {report.observations} observations, "
            f"{report.runs} log entries"
        )
