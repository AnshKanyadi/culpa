"""Team management API routes."""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..dependencies import require_user
from ..storage.team_repository import TeamRepository, InviteRepository
from ..storage.user_repository import UserRepository
from ..services.email import _send, _wrap
from culpa.utils.ids import generate_ulid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/teams", tags=["teams"])

team_repo = TeamRepository()
invite_repo = InviteRepository()
user_repo = UserRepository()


class CreateTeamRequest(BaseModel):
    """Payload for creating a new team."""
    name: str


class InviteRequest(BaseModel):
    """Payload for inviting a user by email."""
    email: str


class VisibilityRequest(BaseModel):
    """Payload for setting session visibility to 'private' or 'team'."""
    visibility: str


def _require_pro(user: dict) -> None:
    """Raise 402 if user is not on the Pro plan."""
    if user.get("plan") != "pro":
        raise HTTPException(status_code=402, detail="Team features require a Pro plan")


@router.post("", status_code=201)
async def create_team(
    body: CreateTeamRequest,
    current_user: dict = Depends(require_user),
) -> dict:
    """Create a new team owned by the current user (Pro only)."""
    _require_pro(current_user)
    team_id = generate_ulid()
    team = team_repo.create(team_id, body.name, current_user["id"])
    return {"team": team}


@router.get("")
async def list_teams(current_user: dict = Depends(require_user)) -> dict:
    """List all teams the current user belongs to."""
    teams = team_repo.list_for_user(current_user["id"])
    return {"teams": teams}


@router.get("/{team_id}")
async def get_team(team_id: str, current_user: dict = Depends(require_user)) -> dict:
    """Get team details including members and pending invites."""
    if not team_repo.is_member(team_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Team not found")
    team = team_repo.get(team_id)
    members = team_repo.get_members(team_id)
    invites = invite_repo.list_pending_for_team(team_id)
    return {"team": team, "members": members, "pending_invites": invites}


@router.post("/{team_id}/invite", status_code=201)
async def invite_member(
    team_id: str,
    body: InviteRequest,
    current_user: dict = Depends(require_user),
) -> dict:
    """Invite a user to a team by email. Only owners and admins can invite."""
    _require_pro(current_user)
    role = team_repo.get_role(team_id, current_user["id"])
    if role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Only owners and admins can invite members")

    team = team_repo.get(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    invite_id = generate_ulid()
    invite = invite_repo.create(invite_id, team_id, body.email, current_user["id"])

    app_url = os.environ.get("CULPA_CLOUD_URL", "https://app.culpa.dev")
    inviter_name = current_user.get("name") or current_user["email"]
    html = _wrap(f"""
    <p><strong>{inviter_name}</strong> invited you to join the team <strong>{team['name']}</strong> on Culpa.</p>
    <p>Team members can view and fork each other's shared sessions.</p>
    <p>
      <a href="{app_url}/settings/team" style="display:inline-block;background:#f75f5f;color:white;text-decoration:none;padding:10px 20px;border-radius:6px;font-weight:600;font-size:13px;">
        Accept Invite
      </a>
    </p>
    <p style="color:#8888a0;font-size:12px;">If you don't have a Culpa account, you'll need to sign up first.</p>
    """)
    try:
        _send(body.email, f"You're invited to join {team['name']} on Culpa", html)
    except Exception:
        pass

    return {"invite": invite}


@router.post("/{team_id}/join")
async def join_team(
    team_id: str,
    current_user: dict = Depends(require_user),
) -> dict:
    """Accept a pending invite and join a team."""
    pending = invite_repo.list_pending_for_email(current_user["email"])
    invite = next((i for i in pending if i["team_id"] == team_id), None)
    if not invite:
        raise HTTPException(status_code=403, detail="No pending invite for this team")

    invite_repo.accept(invite["id"])
    team_repo.add_member(team_id, current_user["id"])
    return {"joined": True, "team_id": team_id}


@router.delete("/{team_id}/members/{user_id}", status_code=204)
async def remove_member(
    team_id: str,
    user_id: str,
    current_user: dict = Depends(require_user),
) -> None:
    """Remove a member from a team. Owners/admins can remove anyone; members can remove themselves."""
    role = team_repo.get_role(team_id, current_user["id"])
    if role not in ("owner", "admin") and user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to remove members")

    removed = team_repo.remove_member(team_id, user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Member not found or is the owner")


@router.patch("/sessions/{session_id}/visibility")
async def set_session_visibility(
    session_id: str,
    body: VisibilityRequest,
    current_user: dict = Depends(require_user),
) -> dict:
    """Set a session's visibility to 'private' or 'team'. Team visibility requires Pro."""
    if body.visibility not in ("private", "team"):
        raise HTTPException(status_code=400, detail="Visibility must be 'private' or 'team'")

    if body.visibility == "team":
        _require_pro(current_user)

    from ..storage.database import get_db
    with get_db() as db:
        result = db.execute(
            "UPDATE sessions SET visibility = ? WHERE id = ? AND user_id = ?",
            (body.visibility, session_id, current_user["id"]),
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")

    return {"session_id": session_id, "visibility": body.visibility}
