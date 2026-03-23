"""
Session CRUD API routes for Prismo server.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..storage.repositories import SessionRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])
session_repo = SessionRepository()


class SessionUploadRequest(BaseModel):
    """Request body for uploading a session."""
    model_config = {"extra": "allow"}


@router.post("", status_code=201)
async def create_session(body: dict[str, Any]) -> dict[str, Any]:
    """
    Upload a new session.

    Accepts the full session JSON as recorded by the Prismo SDK.
    """
    try:
        session = session_repo.create(body)
        if session is None:
            raise HTTPException(status_code=500, detail="Failed to create session")
        return {
            "session_id": session["id"],
            "name": session["name"],
            "status": session["status"],
            "event_count": len(session.get("events", [])),
        }
    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=str(e))


@router.get("")
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
) -> dict[str, Any]:
    """List all sessions with pagination and filtering."""
    return session_repo.list(page=page, page_size=page_size, status=status, search=search)


@router.get("/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    """Get a session with all its events."""
    session = session_repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str) -> None:
    """Delete a session and all its events."""
    deleted = session_repo.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")


@router.get("/{session_id}/stats")
async def get_session_stats(session_id: str) -> dict[str, Any]:
    """Get aggregated stats for a session."""
    session = session_repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return {
        "session_id": session_id,
        "summary": session.get("summary", {}),
        "duration_ms": session.get("duration_ms"),
        "event_count": len(session.get("events", [])),
    }


@router.get("/{session_id}/diff")
async def get_session_diff(session_id: str) -> dict[str, Any]:
    """Get all file diffs across a session."""
    session = session_repo.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    file_changes: dict[str, list[dict[str, Any]]] = {}
    for event in session.get("events", []):
        if event.get("event_type") == "file_change":
            path = event.get("file_path", "")
            if path not in file_changes:
                file_changes[path] = []
            file_changes[path].append({
                "event_id": event.get("event_id"),
                "operation": event.get("operation"),
                "diff": event.get("diff"),
                "timestamp": event.get("timestamp"),
            })

    return {"session_id": session_id, "files": file_changes}
