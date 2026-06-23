"""Public/SaaS mode authentication helpers."""

from typing import Optional

from app.config import get_settings


def is_public_mode() -> bool:
    """Return True if the app is running in public/SaaS mode."""
    settings = get_settings()
    return settings.APP_ENV not in ("local", "")


def public_base_url() -> Optional[str]:
    """Return the public-facing base URL for webhooks/SaaS, or None if not set."""
    settings = get_settings()
    return settings.PUBLIC_BASE_URL
