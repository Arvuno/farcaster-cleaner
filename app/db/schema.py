"""Database schema and migrations."""

import sqlite3
from typing import Optional

from app.config import SQLITE_PATH

# ---------------------------------------------------------------------------
# DDL Statements
# ---------------------------------------------------------------------------

DDL_TG_USERS = """
CREATE TABLE IF NOT EXISTS tg_users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    is_bot INTEGER DEFAULT 0,
    is_admin INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DDL_FARCASTER_ACCOUNTS = """
CREATE TABLE IF NOT EXISTS farcaster_accounts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    fid INTEGER NOT NULL UNIQUE,
    username TEXT,
    display_name TEXT,
    avatar_url TEXT,
    is_primary INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES tg_users(id)
);
"""

DDL_SIGNER_CREDENTIALS = """
CREATE TABLE IF NOT EXISTS signer_credentials (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    farcaster_account_id INTEGER,
    signer_uuid TEXT NOT NULL UNIQUE,
    api_key TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES tg_users(id),
    FOREIGN KEY (farcaster_account_id) REFERENCES farcaster_accounts(id)
);
"""

DDL_SCAN_SESSIONS = """
CREATE TABLE IF NOT EXISTS scan_sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    farcaster_account_id INTEGER,
    job_id TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'prepared',
    mode TEXT DEFAULT 'all',
    include_recasts INTEGER DEFAULT 0,
    total_casts INTEGER DEFAULT 0,
    fetched_casts INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES tg_users(id),
    FOREIGN KEY (farcaster_account_id) REFERENCES farcaster_accounts(id)
);
"""

DDL_SCANNED_CASTS = """
CREATE TABLE IF NOT EXISTS scanned_casts (
    id INTEGER PRIMARY KEY,
    scan_session_id INTEGER NOT NULL,
    cast_hash TEXT NOT NULL,
    fid INTEGER,
    text TEXT,
    timestamp TIMESTAMP,
    parent_hash TEXT,
    root_parent_hash TEXT,
    kind TEXT DEFAULT 'unknown',
    was_selected INTEGER DEFAULT 0,
    was_deleted INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scan_session_id) REFERENCES scan_sessions(id)
);
"""

DDL_ABUSE_CONFIRM_FAIL = """
CREATE TABLE IF NOT EXISTS abuse_confirm_fail (
    id INTEGER PRIMARY KEY,
    job_id TEXT NOT NULL,
    cast_hash TEXT NOT NULL,
    attempt_count INTEGER DEFAULT 0,
    response_code INTEGER,
    response_body TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DDL_AUDIT_EVENTS = """
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    event_type TEXT NOT NULL,
    event_data TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DDL_SCHEMA_MIGRATIONS = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    id INTEGER PRIMARY KEY,
    version TEXT NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# List of all DDL statements in order
ALL_DDLS = [
    DDL_TG_USERS,
    DDL_FARCASTER_ACCOUNTS,
    DDL_SIGNER_CREDENTIALS,
    DDL_SCAN_SESSIONS,
    DDL_SCANNED_CASTS,
    DDL_ABUSE_CONFIRM_FAIL,
    DDL_AUDIT_EVENTS,
    DDL_SCHEMA_MIGRATIONS,
]


# ---------------------------------------------------------------------------
# Schema Management
# ---------------------------------------------------------------------------

def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create all tables if they don't exist.

    This is a idempotent operation - running it multiple times
    is safe as all statements use CREATE TABLE IF NOT EXISTS.
    """
    cursor = conn.cursor()
    for ddl in ALL_DDLS:
        cursor.execute(ddl)
    conn.commit()


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply any pending database migrations.

    In production, this would check schema_migrations table and apply
    any new migrations that haven't been run yet.
    """
    cursor = conn.cursor()

    # Ensure the migrations table exists first
    cursor.execute(DDL_SCHEMA_MIGRATIONS)

    # Get applied migrations
    cursor.execute("SELECT version FROM schema_migrations ORDER BY applied_at")
    applied = {row[0] for row in cursor.fetchall()}

    # Define migrations here as they're added
    migrations = {
        "1.0.0": [
            # Initial schema - already covered by ensure_schema
        ],
    }

    # Apply any pending migrations
    for version, statements in migrations.items():
        if version not in applied:
            for stmt in statements:
                cursor.execute(stmt)
            cursor.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
            conn.commit()


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory set."""
    conn = sqlite3.Connection(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    return conn
