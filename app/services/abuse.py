"""Abuse detection and rate limiting."""

from typing import Optional

from app.store import Store


def check_abuse(user_id: int, store: Store) -> bool:
    """Check if a user has exceeded abuse thresholds.

    Args:
        user_id: The user's Telegram ID.
        store: The Store instance.

    Returns:
        True if abuse is detected (user should be blocked), False otherwise.
    """
    failed_confirmations = store.get_failed_confirmations(user_id)
    return failed_confirmations >= 5


def record_failed_confirmation(user_id: int, store: Store) -> None:
    """Record a failed confirmation attempt for a user.

    Args:
        user_id: The user's Telegram ID.
        store: The Store instance.
    """
    store.increment_failed_confirmations(user_id)


def reset_failures(user_id: int, store: Store) -> None:
    """Reset all failure counters for a user.

    Args:
        user_id: The user's Telegram ID.
        store: The Store instance.
    """
    store.reset_failed_confirmations(user_id)


def audit_event_count(user_id: int, event_type: str, store: Store) -> int:
    """Get the count of a specific event type for a user.

    Args:
        user_id: The user's Telegram ID.
        event_type: The type of event (e.g., "scan", "delete").
        store: The Store instance.

    Returns:
        The number of events of the given type.
    """
    return store.get_event_count(user_id, event_type)


def audit_event_sum_casts_deleted_today(user_id: int, store: Store) -> int:
    """Get the total number of casts deleted by a user today.

    Args:
        user_id: The user's Telegram ID.
        store: The Store instance.

    Returns:
        Total casts deleted today.
    """
    return store.get_casts_deleted_today(user_id)


def add_audit_event(
    user_id: int,
    event_type: str,
    details: dict,
    store: Store,
) -> None:
    """Record an audit event for a user.

    Args:
        user_id: The user's Telegram ID.
        event_type: The type of event.
        details: Additional details about the event.
        store: The Store instance.
    """
    store.add_audit_event(user_id, event_type, details)
