"""SQLite database setup and migrations."""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = str(Path.home() / ".culpa" / "culpa.db")

_connection: sqlite3.Connection | None = None


def get_db_path() -> str:
    """Return the database path from env or the default ~/.culpa/culpa.db."""
    return os.environ.get("CULPA_DB_PATH", DEFAULT_DB_PATH)


def init_db(db_path: str | None = None) -> sqlite3.Connection:
    """Create tables if needed and return the database connection."""
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
    """Return the active connection, initializing if needed."""
    global _connection
    if _connection is None:
        _connection = init_db()
    return _connection


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a database connection with automatic commit/rollback."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Create or update the database schema."""
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

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            plan TEXT NOT NULL DEFAULT 'free',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            key_hash TEXT NOT NULL,
            key_prefix TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT 'Default',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_used_at TEXT,
            revoked_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
        CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);

        CREATE TABLE IF NOT EXISTS teams (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS team_members (
            team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role TEXT NOT NULL DEFAULT 'member',
            joined_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (team_id, user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);

        CREATE TABLE IF NOT EXISTS team_invites (
            id TEXT PRIMARY KEY,
            team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            email TEXT NOT NULL,
            invited_by TEXT NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            accepted_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_team_invites_email ON team_invites(email);
    """)
    conn.commit()

    # SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN,
    # so we catch OperationalError for columns that already exist.
    for col_sql in [
        "ALTER TABLE sessions ADD COLUMN user_id TEXT REFERENCES users(id)",
        "ALTER TABLE sessions ADD COLUMN expires_at TEXT",
        "ALTER TABLE sessions ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'",
    ]:
        try:
            conn.execute(col_sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass

    for col_sql in [
        "ALTER TABLE users ADD COLUMN stripe_customer_id TEXT",
        "ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT",
        "ALTER TABLE users ADD COLUMN plan_expires_at TEXT",
        "ALTER TABLE users ADD COLUMN email_notifications INTEGER NOT NULL DEFAULT 1",
    ]:
        try:
            conn.execute(col_sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass

    logger.debug("Database migrations complete")
