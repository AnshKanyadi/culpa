"""
Fork execution API routes for Prismo server.
"""

from __future__ import annotations

import logging
import sys
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..storage.repositories import ForkRepository, SessionRepository

logger = logging.getLogger(__name__)
router = APIRouter(tags=["forks"])
fork_repo = ForkRepository()
session_repo = SessionRepository()


class ForkRequest(BaseModel):
    """Request body for creating a fork."""
    fork_point_event_id: str
    injected_response: str
    injected_tool_calls: list[dict[str, Any]] = []


@router.post("/api/sessions/{session_id}/fork")
async def create_fork(session_id: str, request: ForkRequest) -> dict[str, Any]:
    """
    Fork a session at a specific event, injecting an alternative LLM response.

    Returns the fork result with both the original and forked event traces.
    """
    # Load the session
    session_data = session_repo.get(session_id)
    if session_data is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    try:
        # Add SDK to path if needed
        sdk_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "sdk")
        if sdk_path not in sys.path:
            sys.path.insert(0, sdk_path)

        from prismo.models import Session
        from prismo.fork import PrismoForker

        # Reconstruct session object
        session = Session.model_validate(session_data)

        # Run the fork
        forker = PrismoForker(session)
        result = forker.fork_at(
            event_id=request.fork_point_event_id,
            new_response=request.injected_response,
            injected_tool_calls=request.injected_tool_calls,
        )

        # Store the fork result
        fork_data = result.model_dump()
        stored = fork_repo.create(fork_data)
        return stored or fork_data

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Fork failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Fork execution failed: {e}")


@router.get("/api/forks/{fork_id}")
async def get_fork(fork_id: str) -> dict[str, Any]:
    """Get a fork result by ID."""
    fork = fork_repo.get(fork_id)
    if fork is None:
        raise HTTPException(status_code=404, detail=f"Fork {fork_id!r} not found")
    return fork


@router.get("/api/sessions/{session_id}/forks")
async def list_session_forks(session_id: str) -> dict[str, Any]:
    """List all forks for a session."""
    if session_repo.get(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    forks = fork_repo.list_for_session(session_id)
    return {"session_id": session_id, "forks": forks}
