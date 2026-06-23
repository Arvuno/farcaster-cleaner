import threading
import queue
from datetime import datetime
from typing import Optional

from app.services.queue.base import QueueBackend, QueueJob, QueueJobStatus, QueueNotSupported


class InMemoryQueue(QueueBackend):
    """Thread-safe in-memory queue implementation using Python's queue module."""

    def __init__(self):
        self._queue: queue.Queue[QueueJob] = queue.Queue()
        self._jobs: dict[str, QueueJob] = {}
        self._lock = threading.Lock()

    def enqueue(self, job: QueueJob) -> None:
        with self._lock:
            job.status = QueueJobStatus.PENDING
            job.created_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            self._jobs[job.job_id] = job
        self._queue.put(job)

    def dequeue(self, timeout: float) -> Optional[QueueJob]:
        try:
            job = self._queue.get(timeout=timeout)
            with self._lock:
                if job.job_id in self._jobs:
                    job.status = QueueJobStatus.RUNNING
                    job.updated_at = datetime.utcnow()
            return job
        except queue.Empty:
            return None

    def ack(self, job: QueueJob) -> None:
        with self._lock:
            job.status = QueueJobStatus.DONE
            job.updated_at = datetime.utcnow()
            if job.job_id in self._jobs:
                self._jobs[job.job_id].status = QueueJobStatus.DONE
                self._jobs[job.job_id].updated_at = datetime.utcnow()

    def nack(self, job: QueueJob, error: str) -> None:
        with self._lock:
            job.attempts += 1
            job.last_error = error
            job.updated_at = datetime.utcnow()
            if job.attempts >= job.max_attempts:
                job.status = QueueJobStatus.FAILED
                if job.job_id in self._jobs:
                    self._jobs[job.job_id].status = QueueJobStatus.FAILED
                    self._jobs[job.job_id].last_error = error
            else:
                # Re-queue the job for retry
                self._queue.put(job)

    def get_status(self, job_id: str) -> QueueJobStatus:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise QueueNotSupported(f"Job {job_id} not found")
            return job.status
