"""Session CRUD API routes."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..storage.repositories import SessionRepository
from ..storage.team_repository import TeamRepository
from ..dependencies import require_user
from ..services.plans import check_can_upload, compute_expires_at, get_user_usage, get_session_count
from ..services.email import send_first_session, send_limit_reached

team_repo = TeamRepository()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])
session_repo = SessionRepository()


@router.post("", status_code=201)
async def create_session(
    body: dict[str, Any],
    current_user: dict = Depends(require_user),
) -> dict[str, Any]:
    """Upload a new session as recorded by the Culpa SDK, scoped to the authenticated user."""
    try:
        plan = current_user.get("plan", "free")
        allowed, reason = check_can_upload(current_user["id"], plan)
        if not allowed:
            raise HTTPException(status_code=402, detail=reason)

        prior_count = get_session_count(current_user["id"])

        expires_at = compute_expires_at(plan)
        session = session_repo.create(body, user_id=current_user["id"], expires_at=expires_at)
        if session is None:
            raise HTTPException(status_code=500, detail="Failed to create session")

        try:
            if prior_count == 0:
                send_first_session(current_user["email"], session["id"], session["name"])

            new_count = prior_count + 1
            if plan == "free" and new_count >= 3:
                send_limit_reached(current_user["email"])
        except Exception:
            pass

        return {
            "session_id": session["id"],
            "name": session["name"],
            "status": session["status"],
            "event_count": len(session.get("events", [])),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=str(e))


@router.get("")
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    scope: str = Query("all"),
    current_user: dict = Depends(require_user),
) -> dict[str, Any]:
    """List sessions with pagination. Scope: 'mine', 'team', or 'all' (mine + team-visible)."""
    if scope == "mine":
        return session_repo.list(
            page=page, page_size=page_size, status=status, search=search,
            user_id=current_user["id"],
        )
    elif scope == "team":
        teammate_ids = team_repo.get_teammate_ids(current_user["id"])
        return session_repo.list_team_sessions(
            page=page, page_size=page_size, status=status, search=search,
            teammate_ids=teammate_ids,
        )
    else:
        teammate_ids = team_repo.get_teammate_ids(current_user["id"])
        return session_repo.list_with_team(
            page=page, page_size=page_size, status=status, search=search,
            user_id=current_user["id"], teammate_ids=teammate_ids,
        )


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    current_user: dict = Depends(require_user),
) -> dict[str, Any]:
    """Get a session by ID. Allowed if owned by user or team-visible to a teammate."""
    session = session_repo.get(session_id, user_id=current_user["id"])
    if session is None:
        session = session_repo.get(session_id)
        if session and session.get("visibility") == "team":
            teammate_ids = team_repo.get_teammate_ids(current_user["id"])
            if session.get("user_id") not in teammate_ids:
                session = None
        else:
            session = None
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    current_user: dict = Depends(require_user),
) -> None:
    """Delete a session and all its events. Must belong to the authenticated user."""
    deleted = session_repo.delete(session_id, user_id=current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")


@router.get("/{session_id}/stats")
async def get_session_stats(
    session_id: str,
    current_user: dict = Depends(require_user),
) -> dict[str, Any]:
    """Return aggregated stats for a session."""
    session = session_repo.get(session_id, user_id=current_user["id"])
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return {
        "session_id": session_id,
        "summary": session.get("summary", {}),
        "duration_ms": session.get("duration_ms"),
        "event_count": len(session.get("events", [])),
    }


@router.get("/{session_id}/diff")
async def get_session_diff(
    session_id: str,
    current_user: dict = Depends(require_user),
) -> dict[str, Any]:
    """Return all file diffs grouped by path across a session."""
    session = session_repo.get(session_id, user_id=current_user["id"])
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
