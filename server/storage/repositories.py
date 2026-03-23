"""
Data access layer for Prismo server.

Provides repository classes for sessions, events, and forks using SQLite.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from .database import get_db

logger = logging.getLogger(__name__)


def _serialize(obj: Any) -> str:
    """Serialize an object to JSON string."""
    return json.dumps(obj, default=str)


def _deserialize(s: str) -> Any:
    """Deserialize a JSON string."""
    if not s:
        return {}
    return json.loads(s)


class SessionRepository:
    """Repository for session CRUD operations."""

    def create(self, session_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new session record."""
        with get_db() as db:
            db.execute(
                """
                INSERT OR REPLACE INTO sessions
                    (id, name, status, metadata_json, started_at, ended_at, duration_ms, summary_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )

            # Upsert all events
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

                # Store file snapshots separately for quick lookup
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

    def get(self, session_id: str) -> Optional[dict[str, Any]]:
        """Get a session by ID with all its events."""
        with get_db() as db:
            row = db.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()

            if row is None:
                return None

            session = dict(row)
            session["metadata"] = _deserialize(session.pop("metadata_json", "{}"))
            session["summary"] = _deserialize(session.pop("summary_json", "{}"))

            # Fetch events
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
    ) -> dict[str, Any]:
        """List sessions with pagination and optional filtering."""
        with get_db() as db:
            conditions = []
            params: list[Any] = []

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
                       duration_ms, summary_json, created_at
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

    def delete(self, session_id: str) -> bool:
        """Delete a session and all its events."""
        with get_db() as db:
            result = db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            return result.rowcount > 0


class EventRepository:
    """Repository for event query operations."""

    def list(
        self,
        session_id: str,
        event_type: Optional[str] = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """List events for a session."""
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
        """Get a single event."""
        with get_db() as db:
            row = db.execute(
                "SELECT data_json FROM events WHERE session_id = ? AND id = ?",
                (session_id, event_id),
            ).fetchone()
            return _deserialize(row["data_json"]) if row else None

    def get_timeline(self, session_id: str) -> list[dict[str, Any]]:
        """Get a simplified timeline view for a session."""
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
    """Repository for fork operations."""

    def create(self, fork_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new fork record."""
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
        """Get a fork by ID."""
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
        """List all forks for a session."""
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
