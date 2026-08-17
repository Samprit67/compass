"""The HTTP layer: a FastAPI app that also serves the web dashboard."""

from .app import create_app

__all__ = ["create_app"]
