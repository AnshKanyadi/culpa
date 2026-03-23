"""
Prismo FastAPI server — main entry point.

Serves the REST API for session management, event queries, and fork execution.
Also serves the React dashboard static files in production.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import sessions, events, forks
from .storage.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Dashboard build directory
DASHBOARD_DIR = Path(__file__).parent.parent / "dashboard" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize resources on startup, clean up on shutdown."""
    logger.info("Prismo server starting up...")
    init_db()
    yield
    logger.info("Prismo server shutting down...")


app = FastAPI(
    title="Prismo API",
    description="Deterministic replay & counterfactual debugging for AI agents",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(sessions.router)
app.include_router(events.router)
app.include_router(forks.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


# Serve React dashboard if built
if DASHBOARD_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DASHBOARD_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_dashboard(full_path: str) -> FileResponse:
        """Serve the React dashboard for all non-API routes."""
        index = DASHBOARD_DIR / "index.html"
        return FileResponse(str(index))

else:
    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint when dashboard is not built."""
        return {
            "message": "Prismo API is running",
            "docs": "/docs",
            "note": "Build the dashboard with: cd dashboard && npm run build",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
