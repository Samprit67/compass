"""The FastAPI application factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from compass import __version__
from compass.errors import CompassError

from .routes import router

_WEB_DIR = Path(__file__).parent.parent / "web"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Compass",
        version=__version__,
        description="Recommend college majors from RIASEC interests, with the reasoning shown.",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    @app.exception_handler(CompassError)
    async def _handle_compass_error(_request: Request, exc: CompassError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"error": str(exc)})

    app.include_router(router, prefix="/api")

    if _WEB_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(_WEB_DIR), html=True), name="web")

    return app
