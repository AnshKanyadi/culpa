"""Event query API routes."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from ..storage.repositories import EventRepository, SessionRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["events"])
event_repo = EventRepository()
session_repo = SessionRepository()


@router.get("/{session_id}/events")
async def list_events(
    session_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(1000, ge=1, le=5000),
) -> dict[str, Any]:
    """List events for a session, optionally filtered by type."""
    if session_repo.get(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    events = event_repo.list(session_id, event_type=event_type, limit=limit)
    return {"session_id": session_id, "events": events, "count": len(events)}


@router.get("/{session_id}/events/{event_id}")
async def get_event(session_id: str, event_id: str) -> dict[str, Any]:
    """Get a single event by ID within a session."""
    event = event_repo.get(session_id, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Event {event_id!r} not found")
    return event


@router.get("/{session_id}/timeline")
async def get_timeline(session_id: str) -> dict[str, Any]:
    """Return a simplified timeline view for a session."""
    if session_repo.get(session_id) is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    timeline = event_repo.get_timeline(session_id)
    return {"session_id": session_id, "timeline": timeline}
