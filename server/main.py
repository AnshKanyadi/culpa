"""Culpa FastAPI server entry point."""

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

from .api import sessions, events, forks, auth, billing, teams
from .storage.database import init_db
from .services.plans import delete_expired_sessions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger(__name__)

DASHBOARD_DIR = Path(__file__).parent.parent / "dashboard" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize database and clean expired sessions on startup."""
    logger.info("Culpa server starting up...")
    init_db()
    deleted = delete_expired_sessions()
    if deleted:
        logger.info(f"Cleaned up {deleted} expired session(s)")
    yield
    logger.info("Culpa server shutting down...")


app = FastAPI(
    title="Culpa API",
    description="Deterministic replay & counterfactual debugging for AI agents",
    version="0.1.0",
    lifespan=lifespan,
)

CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,https://app.culpa.dev"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(events.router)
app.include_router(forks.router)
app.include_router(billing.router)
app.include_router(teams.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


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
        """Fallback root when dashboard is not built."""
        return {
            "message": "Culpa API is running",
            "docs": "/docs",
            "note": "Build the dashboard with: cd dashboard && npm run build",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
