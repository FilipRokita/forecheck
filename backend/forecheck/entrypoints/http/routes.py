"""The read-only API."""

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import PlainTextResponse

from forecheck.application import attribution
from forecheck.application.queries import UnknownStationError
from forecheck.domain.types import MIN_LEAD_DAYS, ModelId, Period, StationId, Variable
from forecheck.entrypoints.http import presenters, schemas
from forecheck.entrypoints.http.deps import ServicesDep, cacheable, only_query_params

router = APIRouter(prefix="/api", dependencies=[Depends(cacheable)])

VariableParam = Annotated[Variable, Query(description="What to look at.")]
PeriodParam = Annotated[
    Period, Query(description="How far back to look, from the latest scored day.")
]


def _unknown_station(error: UnknownStationError) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown station: {error}")


@router.get(
    "/health",
    response_model=schemas.HealthOut,
    tags=["meta"],
    dependencies=[Depends(only_query_params())],
)
def health() -> schemas.HealthOut:
    return schemas.HealthOut(status="ok")


@router.get(
    "/meta",
    response_model=schemas.MetaOut,
    tags=["meta"],
    dependencies=[Depends(only_query_params())],
)
def meta(services: ServicesDep) -> schemas.MetaOut:
    reports = services.reports
    rules = reports.rules
    status_view = reports.status()
    return schemas.MetaOut(
        stations=[presenters.station_out(s) for s in reports.catalog.stations],
        models=[schemas.ModelOut(id=m.id, label=m.label) for m in reports.models()],
        variables=[presenters.variable_out(v, rules) for v in Variable],
        periods=[
            schemas.PeriodOut(id=p.value, label=presenters.PERIOD_LABELS[p], days=p.days)
            for p in Period
        ],
        min_samples=rules.min_samples,
        precipitation_threshold_mm=rules.precipitation_threshold_mm,
        ranking_lead_max=rules.ranking_lead_max,
        attribution=schemas.AttributionOut(
            open_meteo=attribution.OPEN_METEO,
            open_meteo_url=attribution.OPEN_METEO_URL,
            open_meteo_licence=attribution.OPEN_METEO_LICENCE,
            imgw_source=attribution.IMGW_SOURCE,
            imgw_processed=attribution.IMGW_PROCESSED,
            imgw_url=attribution.IMGW_URL,
        ),
        status=schemas.StatusOut(
            sample_data=status_view.sample_data,
            latest_scored_day=status_view.latest_scored_day,
            waiting_forecasts=status_view.waiting_forecasts,
            last_runs=[
                schemas.RunOut(kind=run.kind, at=run.at, ok=run.ok, message=run.message)
                for run in status_view.last_runs.values()
            ],
        ),
    )


@router.get(
    "/stations/{station_id}/verdict",
    response_model=schemas.VerdictOut,
    tags=["scores"],
    dependencies=[Depends(only_query_params("variable", "period"))],
)
def verdict(
    station_id: str, variable: VariableParam, period: PeriodParam, services: ServicesDep
) -> schemas.VerdictOut:
    reports = services.reports
    try:
        view = reports.verdict(StationId(station_id), variable, period)
    except UnknownStationError as error:
        raise _unknown_station(error) from error

    catalog = reports.catalog
    ranking = [
        schemas.RankedModelOut.model_validate(
            {
                "model": ranked.model,
                "label": presenters.model_label(catalog, ranked.model),
                "rank": ranked.rank,
                **presenters.figures(ranked.stats),
            }
        )
        for ranked in view.verdict.ranking
    ]
    best = view.verdict.best
    return schemas.VerdictOut(
        station=presenters.station_out(view.station),
        variable=variable.value,
        period=period.value,
        window=presenters.window_out(view.window),
        lead_from=MIN_LEAD_DAYS,
        lead_to=reports.rules.ranking_lead_max,
        best_model=best,
        best_model_label=presenters.model_label(catalog, best) if best else None,
        trust_days=view.verdict.trust_days,
        next_day=presenters.figure_out(view.verdict.next_day) if view.verdict.next_day else None,
        scored_days=view.scored_days,
        ranking=ranking,
    )


@router.get(
    "/stations/{station_id}/horizon",
    response_model=schemas.HorizonOut,
    tags=["scores"],
    dependencies=[Depends(only_query_params("variable", "period"))],
)
def horizon(
    station_id: str, variable: VariableParam, period: PeriodParam, services: ServicesDep
) -> schemas.HorizonOut:
    reports = services.reports
    try:
        view = reports.horizon(StationId(station_id), variable, period)
    except UnknownStationError as error:
        raise _unknown_station(error) from error

    models = [
        schemas.ModelHorizonOut(
            model=spec.id,
            label=spec.label,
            leads=[
                schemas.LeadFigureOut.model_validate(
                    {"lead_days": lead, **presenters.figures(stats)}
                )
                for lead, stats in sorted(view.stats.get(spec.id, {}).items())
            ],
        )
        for spec in reports.models()
    ]
    return schemas.HorizonOut(
        station=presenters.station_out(view.station),
        variable=variable.value,
        period=period.value,
        window=presenters.window_out(view.window),
        metric=presenters.metric_of(variable),
        trust_threshold=reports.rules.trust_thresholds[variable],
        models=models,
    )


@router.get(
    "/comparison",
    response_model=schemas.ComparisonOut,
    tags=["scores"],
    dependencies=[Depends(only_query_params("variable", "period", "lead_days"))],
)
def comparison(
    variable: VariableParam,
    period: PeriodParam,
    services: ServicesDep,
    lead_days: Annotated[int, Query(ge=1, le=7, description="Days ahead.")] = MIN_LEAD_DAYS,
) -> schemas.ComparisonOut:
    reports = services.reports
    view = reports.comparison(variable, period, lead_days)
    return schemas.ComparisonOut(
        variable=variable.value,
        period=period.value,
        lead_days=lead_days,
        window=presenters.window_out(view.window),
        metric=presenters.metric_of(variable),
        rows=[
            schemas.ComparisonRowOut(
                station=presenters.station_out(row.station),
                best_model=row.best.model if row.best else None,
                best_model_label=presenters.model_label(reports.catalog, row.best.model)
                if row.best
                else None,
                figures=presenters.figure_out(row.best.stats) if row.best else None,
            )
            for row in view.rows
        ],
    )


@router.get(
    "/stations/{station_id}/export.csv",
    response_class=PlainTextResponse,
    tags=["scores"],
    responses={200: {"content": {"text/csv": {}}, "description": "Scores per model and lead."}},
    dependencies=[Depends(only_query_params("variable", "period"))],
)
def export_csv(
    station_id: str, variable: VariableParam, period: PeriodParam, services: ServicesDep
) -> Response:
    reports = services.reports
    try:
        station = reports.catalog.station(StationId(station_id))
        if station is None:
            raise UnknownStationError(station_id)
        rows = reports.export_rows(station.id, variable, period)
    except UnknownStationError as error:
        raise _unknown_station(error) from error

    buffer = io.StringIO()
    # The licence terms ask for attribution on derived products, so the file carries it.
    for line in attribution.LINES:
        buffer.write(f"# {line}\n")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(presenters.export_header())
    for row in rows:
        writer.writerow(presenters.export_row(station, variable, period, row))
    filename = f"forecheck-{station.id}-{variable.value}-{period.value}.csv"
    return Response(
        buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


__all__ = ["ModelId", "router"]
