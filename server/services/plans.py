"""Plan enforcement for free vs pro tier limits."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..storage.database import get_db

PLAN_LIMITS = {
    "free": {
        "max_sessions": 3,
        "retention_days": 7,
        "max_forks_per_session": 5,
    },
    "pro": {
        "max_sessions": None,
        "retention_days": 90,
        "max_forks_per_session": None,
    },
}


def get_limits(plan: str) -> dict[str, Any]:
    """Return the limits dict for a plan, defaulting to free."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


def get_session_count(user_id: str) -> int:
    """Count how many sessions a user currently has stored."""
    with get_db() as db:
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM sessions WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return row["cnt"]


def get_fork_count(session_id: str) -> int:
    """Count existing forks for a session."""
    with get_db() as db:
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM forks WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return row["cnt"]


def check_can_upload(user_id: str, plan: str) -> tuple[bool, str]:
    """Check if user can upload a new session. Returns (allowed, reason)."""
    limits = get_limits(plan)
    max_sessions = limits["max_sessions"]
    if max_sessions is not None:
        count = get_session_count(user_id)
        if count >= max_sessions:
            return False, (
                f"Free tier limited to {max_sessions} cloud sessions. "
                "Upgrade to Pro for unlimited storage."
            )
    return True, ""


def check_can_fork(session_id: str, plan: str) -> tuple[bool, str]:
    """Check if user can create another fork. Returns (allowed, reason)."""
    limits = get_limits(plan)
    max_forks = limits["max_forks_per_session"]
    if max_forks is not None:
        count = get_fork_count(session_id)
        if count >= max_forks:
            return False, (
                f"Free tier limited to {max_forks} forks per session. "
                "Upgrade to Pro for unlimited fork history."
            )
    return True, ""


def compute_expires_at(plan: str) -> str:
    """Compute the ISO expiry timestamp for a new session based on plan retention."""
    limits = get_limits(plan)
    days = limits["retention_days"]
    expires = datetime.now(timezone.utc) + timedelta(days=days)
    return expires.isoformat()


def delete_expired_sessions() -> int:
    """Delete sessions past their expires_at and return the count deleted."""
    with get_db() as db:
        now = datetime.now(timezone.utc).isoformat()
        result = db.execute(
            "DELETE FROM sessions WHERE expires_at IS NOT NULL AND expires_at < ?",
            (now,),
        )
        return result.rowcount


def get_user_usage(user_id: str, plan: str) -> dict[str, Any]:
    """Return usage stats for the dashboard settings page."""
    limits = get_limits(plan)
    session_count = get_session_count(user_id)

    with get_db() as db:
        row = db.execute(
            "SELECT MIN(expires_at) as earliest FROM sessions WHERE user_id = ? AND expires_at IS NOT NULL",
            (user_id,),
        ).fetchone()
        earliest_expiry = row["earliest"] if row else None

    return {
        "session_count": session_count,
        "session_limit": limits["max_sessions"],
        "retention_days": limits["retention_days"],
        "max_forks_per_session": limits["max_forks_per_session"],
        "earliest_expiry": earliest_expiry,
        "at_limit": limits["max_sessions"] is not None and session_count >= limits["max_sessions"],
    }
