"""User preferences management."""

from dataclasses import dataclass
from typing import Optional

from app.store import Store


@dataclass
class UserPreferences:
    """User preferences for the application."""

    notification_enabled: bool = True
    default_mode: str = "all"
    default_count: int = 150


def get_preferences(user_id: int) -> UserPreferences:
    """Get preferences for a user.

    Args:
        user_id: The Telegram user ID.

    Returns:
        UserPreferences with the user's settings (defaults if not set).
    """
    store = Store()
    prefs = store.get_user_preferences(user_id)
    if prefs is None:
        return UserPreferences()
    return prefs


def save_preferences(user_id: int, prefs: UserPreferences) -> None:
    """Save preferences for a user.

    Args:
        user_id: The Telegram user ID.
        prefs: The UserPreferences to save.
    """
    store = Store()
    store.save_user_preferences(user_id, prefs)
