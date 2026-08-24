from __future__ import annotations

from fastapi import FastAPI


def create_runtime_app() -> FastAPI:
    """Create the configured runtime application for Uvicorn."""
    from portproject_rag.api import app

    return app
