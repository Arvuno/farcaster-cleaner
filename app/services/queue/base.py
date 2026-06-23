from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class QueueJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueueJob:
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_type: str = ""
    payload: dict = field(default_factory=dict)
    status: QueueJobStatus = QueueJobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    attempts: int = 0
    max_attempts: int = 3
    last_error: Optional[str] = None


class QueueNotImplemented(Exception):
    """Raised when a queue operation is not implemented for the current backend."""
    pass


class QueueNotSupported(Exception):
    """Raised when a queue operation is not supported by the current backend."""
    pass


class QueueBackend(ABC):
    """Abstract base class for queue backends."""

    @abstractmethod
    def enqueue(self, job: QueueJob) -> None:
        """Add a job to the queue."""
        raise QueueNotImplemented

    @abstractmethod
    def dequeue(self, timeout: float) -> Optional[QueueJob]:
        """Remove and return a job from the queue. Blocks for up to timeout seconds."""
        raise QueueNotImplemented

    @abstractmethod
    def ack(self, job: QueueJob) -> None:
        """Acknowledge successful processing of a job."""
        raise QueueNotImplemented

    @abstractmethod
    def nack(self, job: QueueJob, error: str) -> None:
        """Mark a job as failed with an error message."""
        raise QueueNotImplemented

    @abstractmethod
    def get_status(self, job_id: str) -> QueueJobStatus:
        """Get the current status of a job by its ID."""
        raise QueueNotImplemented


# Global queue backend instance
_queue_backend: Optional[QueueBackend] = None


def enqueue_delete_job(job_id: str, target_hashes: list, tenant_id: str) -> None:
    """Enqueue a delete job for processing."""
    job = QueueJob(
        job_type="delete",
        payload={
            "job_id": job_id,
            "target_hashes": target_hashes,
            "tenant_id": tenant_id,
        },
    )
    backend = get_queue_backend()
    backend.enqueue(job)


def get_queue_backend() -> QueueBackend:
    """Get the configured queue backend instance."""
    global _queue_backend
    if _queue_backend is None:
        from app.services.queue.in_memory import InMemoryQueue
        _queue_backend = InMemoryQueue()
    return _queue_backend
