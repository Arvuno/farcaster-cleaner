"""Deletion job management with confirmation flow."""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from app.models import DeleteJob, JobStatus
from app.store import Store


class DeletionGateError(Exception):
    """Raised when a deletion operation is not allowed."""
    pass


def _generate_confirmation_phrase() -> str:
    """Generate a random confirmation phrase for a deletion job."""
    words = ["delete", "confirm", "proceed", "remove", "erase"]
    return " ".join(uuid.uuid4().hex[:4] for _ in range(4))


def prepare(
    user_id: int,
    target_hashes: List[str],
    store: Store,
) -> Tuple[str, str]:
    """Prepare a deletion job and return (job_id, confirmation_phrase)."""
    job_id = str(uuid.uuid4())
    confirmation_phrase = _generate_confirmation_phrase()

    job = DeleteJob(
        id=job_id,
        status=JobStatus.PREPARED,
        total=len(target_hashes),
        deleted=0,
        failed=0,
        skipped=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        confirmation_phrase=confirmation_phrase,
        target_hashes=target_hashes,
    )
    store.save_delete_job(user_id, job)
    return job_id, confirmation_phrase


def confirm_and_start(
    job_id: str,
    confirmation_phrase: str,
    user_id: int,
    store: Store,
) -> DeleteJob:
    """Confirm a deletion job with the phrase and start execution."""
    job = store.get_delete_job(job_id)
    if job is None:
        raise DeletionGateError(f"Job {job_id} not found")

    if job.confirmation_phrase != confirmation_phrase:
        raise DeletionGateError("Invalid confirmation phrase")

    job.status = JobStatus.RUNNING
    job.updated_at = datetime.utcnow()
    store.update_delete_job(job)
    return job


def cancel(job_id: str, user_id: int, store: Store) -> DeleteJob:
    """Cancel a deletion job."""
    job = store.get_delete_job(job_id)
    if job is None:
        raise DeletionGateError(f"Job {job_id} not found")

    job.status = JobStatus.CANCELLED
    job.updated_at = datetime.utcnow()
    store.update_delete_job(job)
    return job


def list_jobs_for_user(user_id: int, store: Store) -> List[DeleteJob]:
    """List all deletion jobs for a user."""
    return store.list_delete_jobs(user_id)


def get_logs_for_user(user_id: int, store: Store) -> List:
    """Get all deletion logs for a user."""
    return store.get_delete_logs(user_id)


def prepare_with_backup_check(
    user_id: int,
    target_hashes: List[str],
    store: Store,
    backup_dir: str,
) -> Tuple[str, str]:
    """Prepare a deletion job after ensuring backup directory exists."""
    import os
    os.makedirs(backup_dir, exist_ok=True)
    return prepare(user_id, target_hashes, store)


def active_job_for_tenant(tenant_id: int, store: Store) -> Optional[DeleteJob]:
    """Get the active (running) deletion job for a tenant, if any."""
    jobs = store.list_delete_jobs(tenant_id)
    for job in jobs:
        if job.status == JobStatus.RUNNING:
            return job
    return None


def collect_selected_casts(session_id: str, store: Store) -> List[str]:
    """Collect all selected cast hashes from a scan session."""
    session = store.get_session(session_id)
    if session is None:
        return []
    return session.selected_hashes.copy()
