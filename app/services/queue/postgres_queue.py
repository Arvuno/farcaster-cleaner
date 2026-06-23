try:
    import psycopg2
    from psycopg2.pool import ThreadedConnectionPool
except ImportError:
    psycopg2 = None
    ThreadedConnectionPool = None

from typing import Optional
from datetime import datetime

from app.services.queue.base import QueueBackend, QueueJob, QueueJobStatus, QueueNotImplemented, QueueNotSupported


class PostgresQueue(QueueBackend):
    """PostgreSQL-based queue implementation using psycopg2."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "farcaster",
        user: str = "postgres",
        password: str = "",
        min_connections: int = 1,
        max_connections: int = 10,
    ):
        if psycopg2 is None:
            raise ImportError("psycopg2 is required for PostgresQueue. Install it with: pip install psycopg2-binary")

        self.pool = ThreadedConnectionPool(
            min_connections,
            max_connections,
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
        )
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema for the queue."""
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS queue_jobs (
                        job_id VARCHAR(36) PRIMARY KEY,
                        job_type VARCHAR(255) NOT NULL,
                        payload JSONB NOT NULL DEFAULT '{}',
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        attempts INTEGER NOT NULL DEFAULT 0,
                        max_attempts INTEGER NOT NULL DEFAULT 3,
                        last_error TEXT
                    )
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_queue_jobs_status
                    ON queue_jobs(status)
                """)
                conn.commit()
        finally:
            self.pool.putconn(conn)

    def enqueue(self, job: QueueJob) -> None:
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO queue_jobs
                    (job_id, job_type, payload, status, created_at, updated_at, attempts, max_attempts, last_error)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        job.job_id,
                        job.job_type,
                        psycopg2.extras.Json(job.payload),
                        job.status.value,
                        job.created_at,
                        job.updated_at,
                        job.attempts,
                        job.max_attempts,
                        job.last_error,
                    ),
                )
                conn.commit()
        finally:
            self.pool.putconn(conn)

    def dequeue(self, timeout: float) -> Optional[QueueJob]:
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                # Select a pending job and mark it as running atomically
                cur.execute(
                    """
                    UPDATE queue_jobs
                    SET status = %s, updated_at = %s, attempts = attempts + 1
                    WHERE job_id = (
                        SELECT job_id FROM queue_jobs
                        WHERE status = 'pending'
                        ORDER BY created_at
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    RETURNING job_id, job_type, payload, status, created_at, updated_at, attempts, max_attempts, last_error
                    """,
                    (QueueJobStatus.RUNNING.value, datetime.utcnow()),
                )
                row = cur.fetchone()
                conn.commit()

                if row is None:
                    return None

                return QueueJob(
                    job_id=row[0],
                    job_type=row[1],
                    payload=row[2],
                    status=QueueJobStatus(row[3]),
                    created_at=row[4],
                    updated_at=row[5],
                    attempts=row[6],
                    max_attempts=row[7],
                    last_error=row[8],
                )
        finally:
            self.pool.putconn(conn)

    def ack(self, job: QueueJob) -> None:
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE queue_jobs
                    SET status = %s, updated_at = %s
                    WHERE job_id = %s
                    """,
                    (QueueJobStatus.DONE.value, datetime.utcnow(), job.job_id),
                )
                conn.commit()
        finally:
            self.pool.putconn(conn)

    def nack(self, job: QueueJob, error: str) -> None:
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                if job.attempts + 1 >= job.max_attempts:
                    # Mark as failed
                    cur.execute(
                        """
                        UPDATE queue_jobs
                        SET status = %s, last_error = %s, updated_at = %s, attempts = attempts + 1
                        WHERE job_id = %s
                        """,
                        (QueueJobStatus.FAILED.value, error, datetime.utcnow(), job.job_id),
                    )
                else:
                    # Put back to pending for retry
                    cur.execute(
                        """
                        UPDATE queue_jobs
                        SET status = %s, last_error = %s, updated_at = %s, attempts = attempts + 1
                        WHERE job_id = %s
                        """,
                        (QueueJobStatus.PENDING.value, error, datetime.utcnow(), job.job_id),
                    )
                conn.commit()
        finally:
            self.pool.putconn(conn)

    def get_status(self, job_id: str) -> QueueJobStatus:
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM queue_jobs WHERE job_id = %s",
                    (job_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise QueueNotSupported(f"Job {job_id} not found")
                return QueueJobStatus(row[0])
        finally:
            self.pool.putconn(conn)
