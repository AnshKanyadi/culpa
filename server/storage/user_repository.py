"""User and API key data access."""
from __future__ import annotations

from typing import Optional

from .database import get_db


class UserRepository:
    """CRUD operations for user accounts."""

    def create(self, id: str, email: str, password_hash: str, name: Optional[str] = None) -> dict:
        """Insert a new user and return the created record."""
        with get_db() as db:
            db.execute(
                "INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)",
                (id, email, password_hash, name)
            )
        return self.get_by_id(id)

    def get_by_id(self, user_id: str) -> Optional[dict]:
        """Fetch a user by ID (excludes password_hash)."""
        with get_db() as db:
            row = db.execute(
                "SELECT id, email, name, plan, created_at FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_by_email(self, email: str) -> Optional[dict]:
        """Fetch a user by email, including password_hash for login verification."""
        with get_db() as db:
            row = db.execute(
                "SELECT id, email, name, plan, created_at, password_hash FROM users WHERE email = ?",
                (email,)
            ).fetchone()
            return dict(row) if row else None

    def email_exists(self, email: str) -> bool:
        """Check whether an email is already registered."""
        with get_db() as db:
            row = db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
            return row is not None


class ApiKeyRepository:
    """CRUD operations for API keys."""

    def create(
        self,
        id: str,
        user_id: str,
        key_hash: str,
        key_prefix: str,
        name: str = "Default",
    ) -> dict:
        """Insert a new API key record and return it."""
        with get_db() as db:
            db.execute(
                "INSERT INTO api_keys (id, user_id, key_hash, key_prefix, name) VALUES (?, ?, ?, ?, ?)",
                (id, user_id, key_hash, key_prefix, name)
            )
        return self.get_by_id(id)

    def get_by_id(self, key_id: str) -> Optional[dict]:
        """Fetch an API key record by ID."""
        with get_db() as db:
            row = db.execute(
                "SELECT id, user_id, key_prefix, name, created_at, last_used_at, revoked_at "
                "FROM api_keys WHERE id = ?",
                (key_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_by_hash(self, key_hash: str) -> Optional[dict]:
        """Look up a non-revoked API key by its SHA-256 hash."""
        with get_db() as db:
            row = db.execute(
                "SELECT id, user_id, key_prefix, name, created_at, last_used_at, revoked_at "
                "FROM api_keys WHERE key_hash = ? AND revoked_at IS NULL",
                (key_hash,)
            ).fetchone()
            return dict(row) if row else None

    def list_for_user(self, user_id: str) -> list[dict]:
        """List all API keys for a user, newest first."""
        with get_db() as db:
            rows = db.execute(
                "SELECT id, user_id, key_prefix, name, created_at, last_used_at, revoked_at "
                "FROM api_keys WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def revoke(self, key_id: str, user_id: str) -> bool:
        """Soft-delete an API key by setting revoked_at. Returns True if a key was revoked."""
        with get_db() as db:
            result = db.execute(
                "UPDATE api_keys SET revoked_at = datetime('now') "
                "WHERE id = ? AND user_id = ? AND revoked_at IS NULL",
                (key_id, user_id)
            )
            return result.rowcount > 0

    def touch_last_used(self, key_id: str) -> None:
        """Update the last_used_at timestamp for an API key."""
        with get_db() as db:
            db.execute(
                "UPDATE api_keys SET last_used_at = datetime('now') WHERE id = ?",
                (key_id,)
            )
