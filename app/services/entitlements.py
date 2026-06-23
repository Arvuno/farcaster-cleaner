"""Entitlement checking based on plan and user role."""

from dataclasses import dataclass
from typing import List

from app.config import is_admin_user
from app.services.plans import PLAN_FREE, PLAN_PRO, PLAN_POWER, PLAN_ADMIN_INTERNAL


@dataclass
class Entitlements:
    """Represents what a user is entitled to based on their plan."""

    max_casts: int
    rate_limit: float
    can_delete: bool
    can_export: bool
    can_include_recasts: bool
    is_priority: bool


class EntitlementDenied(Exception):
    """Raised when a user attempts something they are not entitled to."""
    pass


def get_entitlements_for_plan(plan_name: str) -> Entitlements:
    """Get entitlements for a given plan name.

    Args:
        plan_name: The plan name (free, pro, power, admin_internal).

    Returns:
        Entitlements for the plan.
    """
    if plan_name == PLAN_ADMIN_INTERNAL:
        return Entitlements(
            max_casts=999999,
            rate_limit=50.0,
            can_delete=True,
            can_export=True,
            can_include_recasts=True,
            is_priority=True,
        )
    elif plan_name == PLAN_POWER:
        return Entitlements(
            max_casts=1000,
            rate_limit=5.0,
            can_delete=True,
            can_export=True,
            can_include_recasts=True,
            is_priority=True,
        )
    elif plan_name == PLAN_PRO:
        return Entitlements(
            max_casts=500,
            rate_limit=2.0,
            can_delete=True,
            can_export=True,
            can_include_recasts=True,
            is_priority=False,
        )
    else:
        return Entitlements(
            max_casts=150,
            rate_limit=1.0,
            can_delete=True,
            can_export=False,
            can_include_recasts=False,
            is_priority=False,
        )


def get_entitlements_for_user(user_id: int) -> Entitlements:
    """Get entitlements for a user based on their plan.

    Args:
        user_id: The user's Telegram ID.

    Returns:
        Entitlements for the user.
    """
    from app.services.plans import get_plan_from_db
    from app.store import Store
    store = Store()
    plan = get_plan_from_db(user_id, store)
    return get_entitlements_for_plan(plan.name)
