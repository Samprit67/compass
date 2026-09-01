"""The FastAPI application factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

from compass import __version__
from compass.errors import CompassError

from .routes import router

_WEB_DIR = Path(__file__).parent.parent / "web"


class _NoCacheStatic(StaticFiles):
    """Serve the SPA without letting the browser hold onto stale JS/CSS."""

    def is_not_modified(self, response_headers, request_headers) -> bool:
        return False

    async def get_response(self, path: str, scope: Scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


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
        app.mount("/", _NoCacheStatic(directory=str(_WEB_DIR), html=True), name="web")

    return app
