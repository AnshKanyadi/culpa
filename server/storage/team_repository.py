"""Team, membership, and invite data access."""
from __future__ import annotations

from typing import Optional
from .database import get_db


class TeamRepository:
    """CRUD operations for teams and their members."""

    def create(self, id: str, name: str, owner_id: str) -> dict:
        """Create a team and add the owner as its first member."""
        with get_db() as db:
            db.execute(
                "INSERT INTO teams (id, name, owner_id) VALUES (?, ?, ?)",
                (id, name, owner_id),
            )
            db.execute(
                "INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, 'owner')",
                (id, owner_id),
            )
        return self.get(id)

    def get(self, team_id: str) -> Optional[dict]:
        """Fetch a team by ID."""
        with get_db() as db:
            row = db.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()
            return dict(row) if row else None

    def list_for_user(self, user_id: str) -> list[dict]:
        """List all teams a user belongs to."""
        with get_db() as db:
            rows = db.execute(
                """SELECT t.id, t.name, t.owner_id, t.created_at, tm.role
                   FROM teams t
                   JOIN team_members tm ON t.id = tm.team_id
                   WHERE tm.user_id = ?
                   ORDER BY t.created_at DESC""",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_members(self, team_id: str) -> list[dict]:
        """List all members of a team with their user info."""
        with get_db() as db:
            rows = db.execute(
                """SELECT u.id, u.email, u.name, tm.role, tm.joined_at
                   FROM team_members tm
                   JOIN users u ON tm.user_id = u.id
                   WHERE tm.team_id = ?
                   ORDER BY tm.joined_at ASC""",
                (team_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def is_member(self, team_id: str, user_id: str) -> bool:
        """Check if a user is a member of a team."""
        with get_db() as db:
            row = db.execute(
                "SELECT 1 FROM team_members WHERE team_id = ? AND user_id = ?",
                (team_id, user_id),
            ).fetchone()
            return row is not None

    def get_role(self, team_id: str, user_id: str) -> Optional[str]:
        """Return the user's role in a team, or None if not a member."""
        with get_db() as db:
            row = db.execute(
                "SELECT role FROM team_members WHERE team_id = ? AND user_id = ?",
                (team_id, user_id),
            ).fetchone()
            return row["role"] if row else None

    def add_member(self, team_id: str, user_id: str, role: str = "member") -> None:
        """Add a user to a team (no-op if already a member)."""
        with get_db() as db:
            db.execute(
                "INSERT OR IGNORE INTO team_members (team_id, user_id, role) VALUES (?, ?, ?)",
                (team_id, user_id, role),
            )

    def remove_member(self, team_id: str, user_id: str) -> bool:
        """Remove a non-owner member from a team. Returns True if removed."""
        with get_db() as db:
            result = db.execute(
                "DELETE FROM team_members WHERE team_id = ? AND user_id = ? AND role != 'owner'",
                (team_id, user_id),
            )
            return result.rowcount > 0

    def get_teammate_ids(self, user_id: str) -> set[str]:
        """Return IDs of all users who share a team with this user (excluding themselves)."""
        with get_db() as db:
            rows = db.execute(
                """SELECT DISTINCT tm2.user_id
                   FROM team_members tm1
                   JOIN team_members tm2 ON tm1.team_id = tm2.team_id
                   WHERE tm1.user_id = ? AND tm2.user_id != ?""",
                (user_id, user_id),
            ).fetchall()
            return {r["user_id"] for r in rows}


class InviteRepository:
    """CRUD operations for team invites."""

    def create(self, id: str, team_id: str, email: str, invited_by: str) -> dict:
        """Create a pending team invite."""
        with get_db() as db:
            db.execute(
                "INSERT INTO team_invites (id, team_id, email, invited_by) VALUES (?, ?, ?, ?)",
                (id, team_id, email, invited_by),
            )
        return self.get(id)

    def get(self, invite_id: str) -> Optional[dict]:
        """Fetch an invite by ID."""
        with get_db() as db:
            row = db.execute("SELECT * FROM team_invites WHERE id = ?", (invite_id,)).fetchone()
            return dict(row) if row else None

    def list_pending_for_team(self, team_id: str) -> list[dict]:
        """List all pending (unaccepted) invites for a team."""
        with get_db() as db:
            rows = db.execute(
                "SELECT * FROM team_invites WHERE team_id = ? AND accepted_at IS NULL ORDER BY created_at DESC",
                (team_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def list_pending_for_email(self, email: str) -> list[dict]:
        """List all pending invites for an email address, including team names."""
        with get_db() as db:
            rows = db.execute(
                """SELECT ti.*, t.name as team_name
                   FROM team_invites ti
                   JOIN teams t ON ti.team_id = t.id
                   WHERE ti.email = ? AND ti.accepted_at IS NULL
                   ORDER BY ti.created_at DESC""",
                (email,),
            ).fetchall()
            return [dict(r) for r in rows]

    def accept(self, invite_id: str) -> bool:
        """Mark an invite as accepted. Returns True if updated."""
        with get_db() as db:
            result = db.execute(
                "UPDATE team_invites SET accepted_at = datetime('now') WHERE id = ? AND accepted_at IS NULL",
                (invite_id,),
            )
            return result.rowcount > 0
