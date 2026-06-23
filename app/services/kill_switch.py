"""Kill switch for emergency service shutdown."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.store import Store


@dataclass
class KillSwitch:
    """Represents the kill switch state."""

    enabled: bool
    reason: Optional[str]
    updated_at: datetime


def get_kill_switch_status() -> KillSwitch:
    """Get the current kill switch status.

    Returns:
        The KillSwitch state.
    """
    store = Store()
    data = store.get_kill_switch()
    if data is None:
        return KillSwitch(enabled=False, reason=None, updated_at=datetime.utcnow())
    return KillSwitch(
        enabled=data.get("enabled", False),
        reason=data.get("reason"),
        updated_at=data.get("updated_at", datetime.utcnow()),
    )
