"""The FastAPI application."""

from fastapi import FastAPI
from fastapi.routing import APIRoute

from forecheck import __version__
from forecheck.entrypoints.http import cron, routes

DESCRIPTION = """
How far can you trust a weather forecast? Open-Meteo models (ICON, ECMWF, GFS) are scored against
IMGW station measurements. Read-only. Data: Open-Meteo.com (CC BY 4.0), IMGW-PIB (processed).
"""


def _operation_id(route: APIRoute) -> str:
    # The function name, so the generated TypeScript types read well: verdict, horizon, comparison.
    return route.name


def create_app() -> FastAPI:
    app = FastAPI(
        title="Forecheck API",
        version=__version__,
        description=DESCRIPTION,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        generate_unique_id_function=_operation_id,
    )
    app.include_router(routes.router)
    app.include_router(cron.router)
    return app
