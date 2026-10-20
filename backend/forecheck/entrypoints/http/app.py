"""The FastAPI application."""

from fastapi import FastAPI

from forecheck import __version__


def create_app() -> FastAPI:
    app = FastAPI(
        title="Forecheck API",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    @app.get("/api/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
