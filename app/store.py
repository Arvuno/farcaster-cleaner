"""SQLite store for persisting casts, jobs, and audit events."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from collections import namedtuple
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from app.config import SQLITE_PATH, ensure_data_dirs, get_settings
from app.models import Cast, CastKind, DeleteJob, DeleteLog, FetchMode, JobStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Row types
# ---------------------------------------------------------------------------

ScannedCastRow = namedtuple(
    "ScannedCastRow",
    "session_id cast_hash selected text timestamp kind parent_hash root_parent_hash url fid",
)


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class Store:
    """SQLite-backed persistence layer for casts, jobs, and audit events."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or SQLITE_PATH
        ensure_data_dirs()
        self._get_conn().__enter__()  # ensure schema initialised on startup

    @contextmanager
    def _get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        """Return a connection to the SQLite database."""
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.commit()
            conn.close()

    # ---------------------------------------------------------------------------
# Schema
    # ---------------------------------------------------------------------------

    def ensure_schema(self) -> None:
        """Create all tables if they do not yet exist."""
        with self._get_conn() as conn:
            self._initialize(conn)

    def _initialize(self, conn: sqlite3.Connection) -> None:
        """Create all schema objects (called within a transaction)."""

        # -- Scan sessions --------------------------------------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_sessions (
                id TEXT PRIMARY KEY,
                fid INTEGER NOT NULL,
                count INTEGER NOT NULL,
                mode TEXT NOT NULL,
                include_recasts INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # -- Scanned casts --------------------------------------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scanned_casts (
                session_id TEXT NOT NULL,
                cast_hash TEXT NOT NULL,
                selected INTEGER NOT NULL DEFAULT 0,
                text TEXT NOT NULL DEFAULT '',
                timestamp TEXT,
                kind TEXT NOT NULL DEFAULT 'unknown',
                parent_hash TEXT,
                root_parent_hash TEXT,
                url TEXT,
                fid INTEGER,
                PRIMARY KEY (session_id, cast_hash),
                FOREIGN KEY (session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE
            )
        """)

        # -- Delete jobs -----------------------------------------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS delete_jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'prepared',
                total INTEGER NOT NULL DEFAULT 0,
                deleted INTEGER NOT NULL DEFAULT 0,
                failed INTEGER NOT NULL DEFAULT 0,
                skipped INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                confirmation_phrase TEXT NOT NULL,
                target_hashes TEXT NOT NULL DEFAULT '[]',
                backup_path TEXT,
                last_message TEXT,
                last_hash TEXT
            )
        """)

        # -- Delete logs -----------------------------------------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS delete_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                cast_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                response_code INTEGER,
                response_body TEXT,
                timestamp TEXT NOT NULL,
                message TEXT,
                FOREIGN KEY (job_id) REFERENCES delete_jobs(id) ON DELETE CASCADE
            )
        """)

        # -- Audit events ----------------------------------------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                casts_deleted INTEGER NOT NULL DEFAULT 0,
                job_id TEXT,
                timestamp TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '{}'
            )
        """)

        # -- Abuse / rate-limiting counters ----------------------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS abuse_counters (
                user_id TEXT PRIMARY KEY,
                fail_count INTEGER NOT NULL DEFAULT 0,
                last_fail_at TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_cast_counts (
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                casts_deleted INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, date)
            )
        """)

    # ---------------------------------------------------------------------------
# Scanned casts
    # ---------------------------------------------------------------------------

    def scanned_casts_list(self, session_id: str) -> List[ScannedCastRow]:
        """Return all casts in a scan session."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM scanned_casts WHERE session_id = ? ORDER BY timestamp DESC",
                (session_id,),
            ).fetchall()
            return [ScannedCastRow(**row) for row in rows]

    def scanned_casts_selected_hashes(self, session_id: str) -> set[str]:
        """Return the set of selected cast hashes for a session."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT cast_hash FROM scanned_casts WHERE session_id = ? AND selected = 1",
                (session_id,),
            ).fetchall()
            return {row["cast_hash"] for row in rows}

    def scanned_casts_set_selected(
        self, session_id: str, cast_hash: str, selected: bool
    ) -> None:
        """Set the selected flag for a single cast."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE scanned_casts SET selected = ? WHERE session_id = ? AND cast_hash = ?",
                (1 if selected else 0, session_id, cast_hash),
            )

    def scanned_casts_set_all(self, session_id: str, selected: bool) -> None:
        """Select or deselect all casts in a session."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE scanned_casts SET selected = ? WHERE session_id = ?",
                (1 if selected else 0, session_id),
            )

    # ---------------------------------------------------------------------------
# Scan sessions
    # ---------------------------------------------------------------------------

    def scan_session_create(
        self,
        fid: int,
        count: int,
        mode: FetchMode,
        include_recasts: bool,
    ) -> str:
        """Create a new scan session and return its id."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO scan_sessions (id, fid, count, mode, include_recasts, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (session_id, fid, count, mode.value, int(include_recasts), now, now),
            )
        return session_id

    def scan_session_get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return a scan session row or None."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM scan_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            return dict(row) if row else None

    def scan_session_get_for_account(self, fid: int) -> Optional[Dict[str, Any]]:
        """Return the most recent scan session for an account."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM scan_sessions WHERE fid = ? ORDER BY created_at DESC LIMIT 1",
                (fid,),
            ).fetchone()
            return dict(row) if row else None

    def scan_session_update_status(self, session_id: str, status: str) -> None:
        """Update the status of a scan session."""
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE scan_sessions SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, session_id),
            )

    def scan_session_list_for_user(self, fid: int) -> List[Dict[str, Any]]:
        """List all scan sessions for a user."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM scan_sessions WHERE fid = ? ORDER BY created_at DESC",
                (fid,),
            ).fetchall()
            return [dict(row) for row in rows]

    # ---------------------------------------------------------------------------
# Jobs
    # ---------------------------------------------------------------------------

    def add_job(
        self,
        confirmation_phrase: str,
        target_hashes: List[str],
        total: int,
    ) -> DeleteJob:
        """Create a new delete job."""
        job_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        job = DeleteJob(
            id=job_id,
            status=JobStatus.PREPARED,
            total=total,
            deleted=0,
            failed=0,
            skipped=0,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
            confirmation_phrase=confirmation_phrase,
            target_hashes=target_hashes,
        )
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO delete_jobs (id, status, total, deleted, failed, skipped, created_at, updated_at, confirmation_phrase, target_hashes, backup_path, last_message, last_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.status.value,
                    job.total,
                    job.deleted,
                    job.failed,
                    job.skipped,
                    now,
                    now,
                    job.confirmation_phrase,
                    json.dumps(job.target_hashes),
                    job.backup_path,
                    job.last_message,
                    job.last_hash,
                ),
            )
        return job

    def get_job(self, job_id: str) -> Optional[DeleteJob]:
        """Return a delete job by id."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM delete_jobs WHERE id = ?", (job_id,)
            ).fetchone()
            if not row:
                return None
            return DeleteJob(
                id=row["id"],
                status=JobStatus(row["status"]),
                total=row["total"],
                deleted=row["deleted"],
                failed=row["failed"],
                skipped=row["skipped"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                confirmation_phrase=row["confirmation_phrase"],
                target_hashes=json.loads(row["target_hashes"]),
                backup_path=row["backup_path"],
                last_message=row["last_message"],
                last_hash=row["last_hash"],
            )

    def update_job(self, job: DeleteJob) -> None:
        """Update an existing delete job."""
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE delete_jobs SET
                    status = ?, total = ?, deleted = ?, failed = ?, skipped = ?,
                    updated_at = ?, confirmation_phrase = ?, target_hashes = ?,
                    backup_path = ?, last_message = ?, last_hash = ?
                WHERE id = ?
                """,
                (
                    job.status.value,
                    job.total,
                    job.deleted,
                    job.failed,
                    job.skipped,
                    now,
                    job.confirmation_phrase,
                    json.dumps(job.target_hashes),
                    job.backup_path,
                    job.last_message,
                    job.last_hash,
                    job.id,
                ),
            )

    def list_jobs(self) -> List[DeleteJob]:
        """Return all delete jobs ordered by created_at desc."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM delete_jobs ORDER BY created_at DESC"
            ).fetchall()
            return [self.get_job(row["id"]) for row in rows]

    # ---------------------------------------------------------------------------
# Delete logs
    # ---------------------------------------------------------------------------

    def add_log(
        self,
        job_id: str,
        cast_hash: str,
        status: str,
        attempt_count: int,
        response_code: Optional[int] = None,
        response_body: Optional[str] = None,
        message: Optional[str] = None,
    ) -> DeleteLog:
        """Add a log entry for a delete operation."""
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO delete_logs (job_id, cast_hash, status, attempt_count, response_code, response_body, timestamp, message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, cast_hash, status, attempt_count, response_code, response_body, now, message),
            )
            log_id = cursor.lastrowid
        return DeleteLog(
            id=log_id,
            job_id=job_id,
            cast_hash=cast_hash,
            status=status,
            attempt_count=attempt_count,
            response_code=response_code,
            response_body=response_body,
            timestamp=datetime.fromisoformat(now),
            message=message,
        )

    def get_logs_for_job(self, job_id: str) -> List[DeleteLog]:
        """Return all log entries for a job."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM delete_logs WHERE job_id = ? ORDER BY timestamp ASC",
                (job_id,),
            ).fetchall()
            return [
                DeleteLog(
                    id=row["id"],
                    job_id=row["job_id"],
                    cast_hash=row["cast_hash"],
                    status=row["status"],
                    attempt_count=row["attempt_count"],
                    response_code=row["response_code"],
                    response_body=row["response_body"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    message=row["message"],
                )
                for row in rows
            ]

    def get_logs_for_user(self, user_id: str) -> List[DeleteLog]:
        """Return all log entries for jobs belonging to a user."""
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT dl.* FROM delete_logs dl
                JOIN delete_jobs dj ON dj.id = dl.job_id
                WHERE dj.confirmation_phrase LIKE ?
                ORDER BY dl.timestamp DESC
                """,
                (f"%{user_id}%",),
            ).fetchall()
            return [
                DeleteLog(
                    id=row["id"],
                    job_id=row["job_id"],
                    cast_hash=row["cast_hash"],
                    status=row["status"],
                    attempt_count=row["attempt_count"],
                    response_code=row["response_code"],
                    response_body=row["response_body"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    message=row["message"],
                )
                for row in rows
            ]

    # ---------------------------------------------------------------------------
# Abuse / rate-limiting
    # ---------------------------------------------------------------------------

    def confirm_fail_get(self, user_id: str) -> int:
        """Return the current fail count for a user."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT fail_count FROM abuse_counters WHERE user_id = ?", (user_id,)
            ).fetchone()
            return row["fail_count"] if row else 0

    def confirm_fail_set(self, user_id: str, fail_count: int) -> None:
        """Set the fail count for a user."""
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO abuse_counters (user_id, fail_count, last_fail_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET fail_count = ?, last_fail_at = ?
                """,
                (user_id, fail_count, now, fail_count, now),
            )

    def confirm_fail_reset(self, user_id: str) -> None:
        """Reset the fail count for a user (on successful confirmation)."""
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM abuse_counters WHERE user_id = ?", (user_id,)
            )

    def audit_event_count(self, user_id: str) -> int:
        """Return total audit event count for a user."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM audit_events WHERE user_id = ?", (user_id,)
            ).fetchone()
            return row["cnt"] if row else 0

    def audit_event_sum_casts_deleted_today(self, user_id: str) -> int:
        """Return total casts deleted today by a user."""
        today = datetime.utcnow().date().isoformat()
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT SUM(casts_deleted) as total FROM daily_cast_counts WHERE user_id = ? AND date = ?",
                (user_id, today),
            ).fetchone()
            return row["total"] if row and row["total"] else 0

    def add_audit_event(
        self,
        user_id: str,
        event_type: str,
        casts_deleted: int = 0,
        job_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an audit event."""
        now = datetime.utcnow().isoformat()
        today = datetime.utcnow().date().isoformat()
        details_json = json.dumps(details or {})

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (user_id, event_type, casts_deleted, job_id, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, event_type, casts_deleted, job_id, now, details_json),
            )
            if casts_deleted > 0:
                conn.execute(
                    """
                    INSERT INTO daily_cast_counts (user_id, date, casts_deleted)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id, date) DO UPDATE SET casts_deleted = daily_cast_counts.casts_deleted + ?
                    """,
                    (user_id, today, casts_deleted, casts_deleted),
                )

    # ---------------------------------------------------------------------------
# Tenant / multi-user helpers
    # ---------------------------------------------------------------------------

    def update_job_tenant(self, job_id: str, user_id: str) -> None:
        """Associate a job with a tenant (user_id)."""
        # In a real app this would be a separate jobs_tenants table.
        # Here we encode user_id in the job record via details.
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE delete_jobs SET last_message = ? WHERE id = ?",
                (f"tenant:{user_id}", job_id),
            )

    def get_job_tenant(self, job_id: str) -> Optional[str]:
        """Return the tenant (user_id) for a job."""
        job = self.get_job(job_id)
        if job and job.last_message and job.last_message.startswith("tenant:"):
            return job.last_message.split(":", 1)[1]
        return None

    def list_jobs_for_tenant(self, user_id: str) -> List[DeleteJob]:
        """List all jobs for a tenant."""
        all_jobs = self.list_jobs()
        return [
            j for j in all_jobs
            if self.get_job_tenant(j.id) == user_id
        ]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

store = Store()
