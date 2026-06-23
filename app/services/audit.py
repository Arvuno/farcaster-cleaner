"""Audit logging for user actions."""

from datetime import datetime
from typing import List, Optional

from app.store import Store


def log_user_connected(
    tg_user_id: int,
    username: Optional[str],
    store: Store,
) -> None:
    """Log a user connection event.

    Args:
        tg_user_id: The user's Telegram ID.
        username: The user's Telegram username.
        store: The Store instance.
    """
    store.add_audit_event(
        user_id=tg_user_id,
        event_type="user_connected",
        details={"username": username, "timestamp": datetime.utcnow().isoformat()},
    )


def log_cast_deleted(
    user_id: int,
    cast_hash: str,
    job_id: str,
    store: Store,
) -> None:
    """Log a cast deletion event.

    Args:
        user_id: The user's Telegram ID.
        cast_hash: The hash of the deleted cast.
        job_id: The deletion job ID.
        store: The Store instance.
    """
    store.add_audit_event(
        user_id=user_id,
        event_type="cast_deleted",
        details={
            "cast_hash": cast_hash,
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


def get_audit_log(
    user_id: int,
    store: Store,
    limit: int = 100,
) -> List:
    """Get audit log entries for a user.

    Args:
        user_id: The user's Telegram ID.
        store: The Store instance.
        limit: Maximum number of entries to return.

    Returns:
        List of audit log entries.
    """
    return store.get_audit_log(user_id, limit=limit)
