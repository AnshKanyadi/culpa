"""
SQLite database setup and migrations for Prismo server.

Creates and manages the database schema for storing sessions, events, and forks.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = str(Path.home() / ".prismo" / "prismo.db")

_connection: sqlite3.Connection | None = None


def get_db_path() -> str:
    """Get the database path from environment or default."""
    return os.environ.get("PRISMO_DB_PATH", DEFAULT_DB_PATH)


def init_db(db_path: str | None = None) -> sqlite3.Connection:
    """
    Initialize the database, creating tables if they don't exist.

    Args:
        db_path: Path to SQLite database file. Uses default if not provided.

    Returns:
        The database connection.
    """
    global _connection

    path = db_path or get_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    _run_migrations(conn)
    _connection = conn
    logger.info(f"Database initialized at {path}")
    return conn


def get_connection() -> sqlite3.Connection:
    """Get the active database connection."""
    global _connection
    if _connection is None:
        _connection = init_db()
    return _connection


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager that yields a database connection."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Run database migrations to create/update schema."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'recording',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            started_at TEXT NOT NULL,
            ended_at TEXT,
            duration_ms REAL,
            summary_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);

        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            parent_event_id TEXT,
            data_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id, sequence);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
        CREATE INDEX IF NOT EXISTS idx_events_parent ON events(parent_event_id);

        CREATE TABLE IF NOT EXISTS forks (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            fork_point_event_id TEXT NOT NULL,
            injected_response TEXT NOT NULL,
            original_events_json TEXT NOT NULL DEFAULT '[]',
            forked_events_json TEXT NOT NULL DEFAULT '[]',
            file_diffs_json TEXT NOT NULL DEFAULT '{}',
            divergence_summary TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_forks_session_id ON forks(session_id);

        CREATE TABLE IF NOT EXISTS file_snapshots (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            content TEXT,
            operation TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_snapshots_session ON file_snapshots(session_id);
        CREATE INDEX IF NOT EXISTS idx_snapshots_path ON file_snapshots(session_id, file_path);
    """)
    conn.commit()
    logger.debug("Database migrations complete")
