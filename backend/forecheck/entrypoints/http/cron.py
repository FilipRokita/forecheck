"""The scheduled job. Vercel Cron calls it with GET and a bearer token."""

from fastapi import APIRouter, Depends, Response, status

from forecheck.entrypoints.http import schemas
from forecheck.entrypoints.http.deps import ServicesDep, require_cron_secret

router = APIRouter(prefix="/api/cron", tags=["cron"], dependencies=[Depends(require_cron_secret)])


@router.get("/collect", response_model=schemas.CycleOut, include_in_schema=False)
def collect(services: ServicesDep, response: Response) -> schemas.CycleOut:
    """Collect today's forecasts, read new measurements and score what can be scored."""
    report = services.daily_cycle.run()
    if not report.ok:
        response.status_code = status.HTTP_502_BAD_GATEWAY
    return schemas.CycleOut(
        ok=report.ok,
        steps=[schemas.CycleStepOut(name=s.name, ok=s.ok, message=s.message) for s in report.steps],
    )
