"""Billing limits enforcement."""

from enum import Enum

from app.services.plans import Plan, get_plan_from_db
from app.store import Store


class LimitExceeded(Exception):
    """Raised when a user exceeds their plan limit."""
    pass


class Tier(Enum):
    """Billing tier levels."""
    FREE = "free"
    PRO = "pro"
    POWER = "power"
    ADMIN_INTERNAL = "admin_internal"


def assert_scan_count_allowed(user_id: int, plan: Plan, store: Store) -> None:
    """Assert that a user is allowed to perform a scan given their plan limits.

    Args:
        user_id: The user's ID.
        plan: The user's plan.
        store: The Store instance.

    Raises:
        LimitExceeded: If the user has exceeded their scan count limit.
    """
    usage = store.get_user_usage(user_id)
    if usage is None:
        return

    scans_today = usage.get("scans_today", 0)
    if scans_today >= plan.max_casts:
        raise LimitExceeded(
            f"Scan limit reached: {scans_today}/{plan.max_casts} scans today. "
            f"Upgrade your plan to increase limits."
        )
