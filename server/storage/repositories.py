"""Data access layer for sessions, events, and forks."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from .database import get_db

logger = logging.getLogger(__name__)


def _serialize(obj: Any) -> str:
    """Serialize an object to a JSON string, using str() as a fallback for non-serializable types."""
    return json.dumps(obj, default=str)


def _deserialize(s: str) -> Any:
    """Deserialize a JSON string, returning empty dict for falsy input."""
    if not s:
        return {}
    return json.loads(s)


class SessionRepository:
    """CRUD operations for sessions and their associated events."""

    def create(self, session_data: dict[str, Any], user_id: Optional[str] = None, expires_at: Optional[str] = None) -> dict[str, Any]:
        """Persist a session and its events, returning the stored session."""
        with get_db() as db:
            db.execute(
                """
                INSERT OR REPLACE INTO sessions
                    (id, name, status, metadata_json, started_at, ended_at, duration_ms, summary_json, user_id, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_data["session_id"],
                    session_data.get("name", ""),
                    session_data.get("status", "completed"),
                    _serialize(session_data.get("metadata", {})),
                    session_data.get("started_at", ""),
                    session_data.get("ended_at"),
                    session_data.get("duration_ms"),
                    _serialize(session_data.get("summary", {})),
                    user_id,
                    expires_at,
                ),
            )

            events = session_data.get("events", [])
            if events:
                db.executemany(
                    """
                    INSERT OR REPLACE INTO events
                        (id, session_id, sequence, type, timestamp, parent_event_id, data_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            e["event_id"],
                            session_data["session_id"],
                            e["sequence"],
                            e["event_type"],
                            e["timestamp"],
                            e.get("parent_event_id"),
                            _serialize(e),
                        )
                        for e in events
                    ],
                )

                file_events = [e for e in events if e.get("event_type") == "file_change"]
                for fe in file_events:
                    db.execute(
                        """
                        INSERT OR REPLACE INTO file_snapshots
                            (id, session_id, event_id, file_path, content, operation)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            fe["event_id"] + "_snap",
                            session_data["session_id"],
                            fe["event_id"],
                            fe.get("file_path", ""),
                            fe.get("content_after"),
                            fe.get("operation", "modify"),
                        ),
                    )

        return self.get(session_data["session_id"])

    def get(self, session_id: str, user_id: Optional[str] = None) -> Optional[dict[str, Any]]:
        """Fetch a session with all its events. If user_id is given, verify ownership."""
        with get_db() as db:
            if user_id is not None:
                row = db.execute(
                    "SELECT * FROM sessions WHERE id = ? AND user_id = ?",
                    (session_id, user_id),
                ).fetchone()
            else:
                row = db.execute(
                    "SELECT * FROM sessions WHERE id = ?", (session_id,)
                ).fetchone()

            if row is None:
                return None

            session = dict(row)
            session["metadata"] = _deserialize(session.pop("metadata_json", "{}"))
            session["summary"] = _deserialize(session.pop("summary_json", "{}"))

            event_rows = db.execute(
                "SELECT data_json FROM events WHERE session_id = ? ORDER BY sequence ASC",
                (session_id,),
            ).fetchall()

            session["events"] = [_deserialize(r["data_json"]) for r in event_rows]
            return session

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """List sessions with pagination and optional filters."""
        with get_db() as db:
            conditions = []
            params: list[Any] = []

            if user_id is not None:
                conditions.append("user_id = ?")
                params.append(user_id)
            if status:
                conditions.append("status = ?")
                params.append(status)
            if search:
                conditions.append("name LIKE ?")
                params.append(f"%{search}%")

            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            total = db.execute(
                f"SELECT COUNT(*) as cnt FROM sessions {where}", params
            ).fetchone()["cnt"]

            offset = (page - 1) * page_size
            rows = db.execute(
                f"""
                SELECT id, name, status, metadata_json, started_at, ended_at,
                       duration_ms, summary_json, created_at, user_id, expires_at
                FROM sessions {where}
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?
                """,
                params + [page_size, offset],
            ).fetchall()

            sessions = []
            for row in rows:
                s = dict(row)
                s["metadata"] = _deserialize(s.pop("metadata_json", "{}"))
                s["summary"] = _deserialize(s.pop("summary_json", "{}"))
                sessions.append(s)

            return {
                "sessions": sessions,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
            }

    def _list_query(
        self,
        page: int,
        page_size: int,
        conditions: list[str],
        params: list[Any],
    ) -> dict[str, Any]:
        """Shared pagination query used by team-aware list methods."""
        with get_db() as db:
            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            total = db.execute(
                f"SELECT COUNT(*) as cnt FROM sessions {where}", params
            ).fetchone()["cnt"]
            offset = (page - 1) * page_size
            rows = db.execute(
                f"""SELECT id, name, status, metadata_json, started_at, ended_at,
                           duration_ms, summary_json, created_at, user_id, expires_at, visibility
                    FROM sessions {where}
                    ORDER BY started_at DESC LIMIT ? OFFSET ?""",
                params + [page_size, offset],
            ).fetchall()
            sessions = []
            for row in rows:
                s = dict(row)
                s["metadata"] = _deserialize(s.pop("metadata_json", "{}"))
                s["summary"] = _deserialize(s.pop("summary_json", "{}"))
                sessions.append(s)
            return {
                "sessions": sessions, "total": total, "page": page,
                "page_size": page_size, "total_pages": (total + page_size - 1) // page_size,
            }

    def list_team_sessions(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
        teammate_ids: Optional[set[str]] = None,
    ) -> dict[str, Any]:
        """List team-visible sessions from teammates."""
        if not teammate_ids:
            return {"sessions": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}
        conditions = [f"user_id IN ({','.join('?' for _ in teammate_ids)})", "visibility = 'team'"]
        params: list[Any] = list(teammate_ids)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if search:
            conditions.append("name LIKE ?")
            params.append(f"%{search}%")
        return self._list_query(page, page_size, conditions, params)

    def list_with_team(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
        user_id: Optional[str] = None,
        teammate_ids: Optional[set[str]] = None,
    ) -> dict[str, Any]:
        """List own sessions combined with team-visible sessions from teammates."""
        ownership_parts = []
        params: list[Any] = []
        if user_id:
            ownership_parts.append("user_id = ?")
            params.append(user_id)
        if teammate_ids:
            placeholders = ','.join('?' for _ in teammate_ids)
            ownership_parts.append(f"(user_id IN ({placeholders}) AND visibility = 'team')")
            params.extend(teammate_ids)
        conditions = [f"({' OR '.join(ownership_parts)})"] if ownership_parts else []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if search:
            conditions.append("name LIKE ?")
            params.append(f"%{search}%")
        return self._list_query(page, page_size, conditions, params)

    def delete(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a session and cascade to events. If user_id given, verify ownership."""
        with get_db() as db:
            if user_id is not None:
                result = db.execute(
                    "DELETE FROM sessions WHERE id = ? AND user_id = ?",
                    (session_id, user_id),
                )
            else:
                result = db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            return result.rowcount > 0


class EventRepository:
    """Read-only query operations for events."""

    def list(
        self,
        session_id: str,
        event_type: Optional[str] = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """List events for a session, optionally filtered by type."""
        with get_db() as db:
            query = "SELECT data_json FROM events WHERE session_id = ?"
            params: list[Any] = [session_id]

            if event_type:
                query += " AND type = ?"
                params.append(event_type)

            query += " ORDER BY sequence ASC LIMIT ?"
            params.append(limit)

            rows = db.execute(query, params).fetchall()
            return [_deserialize(r["data_json"]) for r in rows]

    def get(self, session_id: str, event_id: str) -> Optional[dict[str, Any]]:
        """Fetch a single event by session and event ID."""
        with get_db() as db:
            row = db.execute(
                "SELECT data_json FROM events WHERE session_id = ? AND id = ?",
                (session_id, event_id),
            ).fetchone()
            return _deserialize(row["data_json"]) if row else None

    def get_timeline(self, session_id: str) -> list[dict[str, Any]]:
        """Return a lightweight timeline with key fields extracted via json_extract."""
        with get_db() as db:
            rows = db.execute(
                """
                SELECT id, sequence, type, timestamp, parent_event_id,
                       json_extract(data_json, '$.model') as model,
                       json_extract(data_json, '$.file_path') as file_path,
                       json_extract(data_json, '$.command') as command,
                       json_extract(data_json, '$.tool_name') as tool_name,
                       json_extract(data_json, '$.latency_ms') as latency_ms,
                       json_extract(data_json, '$.exit_code') as exit_code
                FROM events
                WHERE session_id = ?
                ORDER BY sequence ASC
                """,
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]


class ForkRepository:
    """CRUD operations for fork results."""

    def create(self, fork_data: dict[str, Any]) -> dict[str, Any]:
        """Persist a fork result and return the stored record."""
        with get_db() as db:
            db.execute(
                """
                INSERT INTO forks
                    (id, session_id, fork_point_event_id, injected_response,
                     original_events_json, forked_events_json, file_diffs_json,
                     divergence_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fork_data["fork_id"],
                    fork_data["session_id"],
                    fork_data["fork_point_event_id"],
                    fork_data["injected_response"],
                    _serialize(fork_data.get("original_events_after", [])),
                    _serialize(fork_data.get("forked_events", [])),
                    _serialize(fork_data.get("file_diffs", {})),
                    fork_data.get("divergence_summary"),
                ),
            )
        return self.get(fork_data["fork_id"])

    def get(self, fork_id: str) -> Optional[dict[str, Any]]:
        """Fetch a fork by ID, deserializing JSON fields."""
        with get_db() as db:
            row = db.execute(
                "SELECT * FROM forks WHERE id = ?", (fork_id,)
            ).fetchone()

            if row is None:
                return None

            fork = dict(row)
            fork["original_events_after"] = _deserialize(fork.pop("original_events_json", "[]"))
            fork["forked_events"] = _deserialize(fork.pop("forked_events_json", "[]"))
            fork["file_diffs"] = _deserialize(fork.pop("file_diffs_json", "{}"))
            return fork

    def list_for_session(self, session_id: str) -> list[dict[str, Any]]:
        """List all forks for a session (summary only, without full event data)."""
        with get_db() as db:
            rows = db.execute(
                """
                SELECT id, session_id, fork_point_event_id, injected_response,
                       divergence_summary, created_at
                FROM forks WHERE session_id = ? ORDER BY created_at DESC
                """,
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]
