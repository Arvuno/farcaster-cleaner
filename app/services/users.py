"""User management and stats."""

from typing import Dict, Optional

from app.store import Store


def get_or_create_user(
    tg_user_id: int,
    username: Optional[str],
    store: Store,
) -> Dict:
    """Get or create a user record.

    Args:
        tg_user_id: The user's Telegram ID.
        username: The user's Telegram username.
        store: The Store instance.

    Returns:
        A dict with user information.
    """
    user = store.get_user(tg_user_id)
    if user is None:
        user = store.create_user(tg_user_id, username)
    else:
        # Update username if changed
        if username and user.get("username") != username:
            user["username"] = username
            store.update_user(user)
    return user


def get_user_stats(user_id: int, store: Store) -> Dict:
    """Get statistics for a user.

    Args:
        user_id: The user's ID.
        store: The Store instance.

    Returns:
        A dict with user statistics.
    """
    usage = store.get_user_usage(user_id)
    jobs = store.list_delete_jobs(user_id)

    total_deleted = sum(job.deleted for job in jobs)
    total_failed = sum(job.failed for job in jobs)
    completed_jobs = sum(1 for job in jobs if job.status == "completed")

    return {
        "user_id": user_id,
        "scans_today": usage.get("scans_today", 0) if usage else 0,
        "casts_deleted_today": usage.get("casts_deleted_today", 0) if usage else 0,
        "total_scans": usage.get("total_scans", 0) if usage else 0,
        "total_casts_deleted": total_deleted,
        "total_jobs": len(jobs),
        "completed_jobs": completed_jobs,
    }
