"""JobManager — orchestrates delete job lifecycle (prepare, start, cancel)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

from app.models import DeleteJob, JobEvent, JobStatus

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


class JobManager:
    """Coordinates delete job creation, execution state, and cancellation."""

    __slots__ = ("_store",)

    def __init__(self, store) -> None:
        self._store = store

    def prepare_job(
        self,
        target_hashes: List[str],
        confirmation_phrase: str,
    ) -> DeleteJob:
        """Create a PREPARED job ready to be started."""
        from app.safety import generate_confirmation_phrase

        phrase = confirmation_phrase or generate_confirmation_phrase()
        job = self._store.add_job(
            confirmation_phrase=phrase,
            target_hashes=target_hashes,
            total=len(target_hashes),
        )
        logger.info("Job %s prepared with %d casts", job.id, job.total)
        return job

    def start_job(
        self,
        job_id: str,
        settings: "Settings",
        publish_fn: Optional[Callable[[str, JobEvent], None]] = None,
    ) -> DeleteJob:
        """Transition a PREPARED job to RUNNING after phrase validation."""
        job = self._store.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        if job.status != JobStatus.PREPARED:
            raise ValueError(f"Job {job_id} is not in PREPARED state (currently {job.status.value})")

        job.status = JobStatus.RUNNING
        job.updated_at = datetime.utcnow()
        self._store.update_job(job)

        event = JobEvent(
            type="status",
            job_id=job_id,
            timestamp=datetime.utcnow(),
            data={"status": job.status.value, "message": "Job started"},
        )
        if publish_fn:
            publish_fn(job_id, event)

        logger.info("Job %s started", job_id)
        return job

    def cancel_job(self, job_id: str) -> DeleteJob:
        """Transition a job to CANCELLED."""
        job = self._store.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        if job.status in (JobStatus.COMPLETED, JobStatus.CANCELLED):
            raise ValueError(f"Job {job_id} is already {job.status.value}")

        job.status = JobStatus.CANCELLED
        job.updated_at = datetime.utcnow()
        self._store.update_job(job)

        logger.info("Job %s cancelled", job_id)
        return job

    def get_job(self, job_id: str) -> Optional[DeleteJob]:
        """Return a job by id."""
        return self._store.get_job(job_id)

    def list_jobs_for_user(self, user_id: str) -> List[DeleteJob]:
        """List all jobs for a given user/tenant."""
        return self._store.list_jobs_for_tenant(user_id)

    def update_job_progress(
        self,
        job_id: str,
        deleted: int,
        failed: int,
        skipped: int,
        last_hash: Optional[str] = None,
        last_message: Optional[str] = None,
    ) -> None:
        """Update job progress counters."""
        job = self._store.get_job(job_id)
        if not job:
            return
        job.deleted = deleted
        job.failed = failed
        job.skipped = skipped
        job.last_hash = last_hash
        job.last_message = last_message
        job.updated_at = datetime.utcnow()
        self._store.update_job(job)

    def complete_job(self, job_id: str, status: JobStatus, last_message: Optional[str] = None) -> None:
        """Mark a job as completed or failed."""
        job = self._store.get_job(job_id)
        if not job:
            return
        job.status = status
        job.last_message = last_message
        job.updated_at = datetime.utcnow()
        self._store.update_job(job)
        logger.info("Job %s completed with status %s", job_id, status.value)
