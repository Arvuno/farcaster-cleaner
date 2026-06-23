"""Usage tracking and reporting."""

from typing import Dict

from app.store import Store


def record_scan(user_id: int, cast_count: int, store: Store) -> None:
    """Record a scan operation for a user.

    Args:
        user_id: The user's Telegram ID.
        cast_count: The number of casts scanned.
        store: The Store instance.
    """
    store.record_scan(user_id, cast_count)


def get_usage_summary(user_id: int, store: Store) -> Dict:
    """Get a summary of usage for a user.

    Args:
        user_id: The user's Telegram ID.
        store: The Store instance.

    Returns:
        A dict with usage statistics.
    """
    usage = store.get_user_usage(user_id)
    if usage is None:
        return {
            "scans_today": 0,
            "casts_deleted_today": 0,
            "total_scans": 0,
            "total_casts_deleted": 0,
        }
    return usage
