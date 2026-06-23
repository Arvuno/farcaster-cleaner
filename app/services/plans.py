"""Plan definitions and plan lookup."""

from dataclasses import dataclass, field
from typing import List

PLAN_FREE = "free"
PLAN_PRO = "pro"
PLAN_POWER = "power"
PLAN_ADMIN_INTERNAL = "admin_internal"


@dataclass
class Plan:
    """Represents a subscription plan with its limits and features."""

    name: str
    max_casts: int
    rate_limit: float
    features: List[str] = field(default_factory=list)


# Plan definitions
_PLANS = {
    PLAN_FREE: Plan(
        name=PLAN_FREE,
        max_casts=150,
        rate_limit=1.0,
        features=["basic_scan", "delete"],
    ),
    PLAN_PRO: Plan(
        name=PLAN_PRO,
        max_casts=500,
        rate_limit=2.0,
        features=["basic_scan", "delete", "recasts", "exports"],
    ),
    PLAN_POWER: Plan(
        name=PLAN_POWER,
        max_casts=1000,
        rate_limit=5.0,
        features=["basic_scan", "delete", "recasts", "exports", "priority_support"],
    ),
    PLAN_ADMIN_INTERNAL: Plan(
        name=PLAN_ADMIN_INTERNAL,
        max_casts=999999,
        rate_limit=50.0,
        features=["basic_scan", "delete", "recasts", "exports", "admin"],
    ),
}


def get_plan_from_db(user_id: int, store: Store) -> Plan:
    """Look up the user's plan from the database.

    Args:
        user_id: The user's ID.
        store: The Store instance.

    Returns:
        The user's Plan.
    """
    plan_name = store.get_user_plan(user_id)
    return _PLANS.get(plan_name, _PLANS[PLAN_FREE])
