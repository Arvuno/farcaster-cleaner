from typing import Optional

from app.services.queue.base import QueueBackend, QueueJob, QueueJobStatus


class RedisQueue(QueueBackend):
    """Redis-based queue implementation. Currently not implemented."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        queue_name: str = "farcaster:queue",
    ):
        raise NotImplementedError("RedisQueue is not yet implemented")

    def enqueue(self, job: QueueJob) -> None:
        raise NotImplementedError("RedisQueue is not yet implemented")

    def dequeue(self, timeout: float) -> Optional[QueueJob]:
        raise NotImplementedError("RedisQueue is not yet implemented")

    def ack(self, job: QueueJob) -> None:
        raise NotImplementedError("RedisQueue is not yet implemented")

    def nack(self, job: QueueJob, error: str) -> None:
        raise NotImplementedError("RedisQueue is not yet implemented")

    def get_status(self, job_id: str) -> QueueJobStatus:
        raise NotImplementedError("RedisQueue is not yet implemented")
