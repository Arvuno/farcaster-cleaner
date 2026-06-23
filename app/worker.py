"""Durable worker that dequeues and processes delete jobs."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from app.models import DeleteJob, JobEvent, JobStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Queue availability
# ---------------------------------------------------------------------------

try:
    import psycopg2
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False

PostgresQueue: Any = None
if _PSYCOPG2_AVAILABLE:
    try:
        from app.services.queue.postgres_queue import PostgresQueue
    except Exception:
        PostgresQueue = None

# ---------------------------------------------------------------------------
# DeleteWorker
# ---------------------------------------------------------------------------


class DeleteWorker:
    """Long-lived worker that processes delete jobs from a queue.

    The worker runs in a durable loop: it dequeues a job, processes each cast
    with retries and rate-limiting, logs results, and updates job status.
    """

    def __init__(
        self,
        queue: Optional[Any],
        store: Any,
        client: Any,
        rate_limit_rps: float = 1.5,
        max_attempts: int = 3,
    ) -> None:
        """
        Args:
            queue:        Queue backend (PostgresQueue when psycopg2 is available).
            store:        Store instance for persistence.
            client:       NeynarClient for API calls.
            rate_limit_rps: Maximum deletes per second.
            max_attempts:   Maximum retry attempts per cast.
        """
        self._queue = queue
        self._store = store
        self._client = client
        self._rate_limit_rps = rate_limit_rps
        self._max_attempts = max_attempts
        self._running = False

    def run(self) -> None:
        """Start the durable processing loop. Blocks until stop() is called."""
        self._running = True
        logger.info("DeleteWorker started (rate=%.1f rps, max_attempts=%d)", self._rate_limit_rps, self._max_attempts)

        while self._running:
            try:
                job_id = self._dequeue()
                if job_id is None:
                    time.sleep(1.0)
                    continue
                self._process_job(job_id)
            except Exception as exc:
                logger.exception("Worker loop error: %s", exc)
                time.sleep(5.0)

        logger.info("DeleteWorker stopped")

    def stop(self) -> None:
        """Gracefully stop the worker after the current job finishes."""
        self._running = False

    # ---------------------------------------------------------------------------
# Internals
    # ---------------------------------------------------------------------------

    def _dequeue(self) -> Optional[str]:
        """Dequeue a job id from the queue, or None if the queue is unavailable."""
        if self._queue is None:
            return None
        try:
            return self._queue.dequeue()
        except Exception as exc:
            logger.warning("Dequeuing failed: %s", exc)
            return None

    def _process_job(self, job_id: str) -> None:
        """Process all casts in a delete job."""
        job = self._store.get_job(job_id)
        if not job:
            logger.warning("Job %s not found, skipping", job_id)
            return

        if job.status == JobStatus.CANCELLED:
            logger.info("Job %s is cancelled, skipping", job_id)
            return

        job.status = JobStatus.RUNNING
        job.updated_at = job.updated_at.__class__.utcnow__()
        self._store.update_job(job)

        deleted = failed = skipped = 0
        last_hash: Optional[str] = None
        last_message: Optional[str] = None

        for cast_hash in job.target_hashes:
            if not self._running:
                logger.info("Job %s interrupted by stop signal", job_id)
                break

            try:
                result = self._delete_cast_with_retry(cast_hash)
                if result["success"]:
                    deleted += 1
                    status_str = "deleted"
                else:
                    failed += 1
                    status_str = "failed"
                    last_message = result.get("error")

                last_hash = cast_hash
                self._store.add_log(
                    job_id=job_id,
                    cast_hash=cast_hash,
                    status=status_str,
                    attempt_count=result.get("attempts", 1),
                    response_code=result.get("code"),
                    response_body=result.get("body"),
                    message=result.get("error"),
                )

            except Exception as exc:
                failed += 1
                last_message = str(exc)
                logger.exception("Error deleting cast %s in job %s", cast_hash, job_id)

            # Rate limiting
            time.sleep(1.0 / self._rate_limit_rps)

            # Progress update
            self._store.update_job(
                self._store.get_job(job_id)  # re-fetch to get latest
            )

        # Finalise job
        final_job = self._store.get_job(job_id)
        if final_job:
            final_job.deleted = deleted
            final_job.failed = failed
            final_job.skipped = skipped
            final_job.last_hash = last_hash
            final_job.last_message = last_message
            if not self._running or final_job.status == JobStatus.CANCELLED:
                final_job.status = JobStatus.CANCELLED
            elif failed == 0:
                final_job.status = JobStatus.COMPLETED
            else:
                final_job.status = JobStatus.FAILED
            self._store.update_job(final_job)

        logger.info(
            "Job %s finished: deleted=%d failed=%d skipped=%d",
            job_id, deleted, failed, skipped,
        )

    def _delete_cast_with_retry(self, cast_hash: str) -> dict:
        """Attempt to delete a cast with retries; return result dict."""
        from app.safety import redact

        last_error: Optional[str] = None
        last_code: Optional[int] = None
        last_body: Optional[str] = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                self._client.delete_cast(cast_hash)
                return {"success": True, "attempts": attempt, "cast_hash": cast_hash}
            except Exception as exc:
                last_error = redact(str(exc))
                if hasattr(exc, "code"):
                    last_code = exc.code
                if last_code == 404:
                    # Already deleted — not a failure
                    return {
                        "success": True,
                        "attempts": attempt,
                        "cast_hash": cast_hash,
                        "error": "Already deleted (404)",
                    }
                if last_code == 429:
                    # Rate limited — retry after backoff
                    time.sleep(2 ** attempt)
                    continue
                if attempt < self._max_attempts:
                    time.sleep(1 * attempt)

        return {
            "success": False,
            "attempts": self._max_attempts,
            "cast_hash": cast_hash,
            "error": last_error,
            "code": last_code,
            "body": last_body,
        }
