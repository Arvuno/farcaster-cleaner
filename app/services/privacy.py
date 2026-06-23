"""Privacy redaction for casts and user data."""

from typing import Optional

from app.models import Cast, CastKind


def redact_cast_content(cast: Cast) -> Cast:
    """Redact sensitive content from a cast.

    Args:
        cast: The Cast to redact.

    Returns:
        A new Cast with redacted content.
    """
    redacted = cast.model_copy()
    # Redact text content
    redacted.text = "[redacted]"
    # Keep URL but mark it as potentially sensitive
    if redacted.url:
        redacted.url = "[redacted-url]"
    return redacted


def redact_user_data(user_id: int) -> None:
    """Redact all data associated with a user.

    Args:
        user_id: The user's Telegram ID.
    """
    from app.store import Store
    store = Store()
    store.redact_user(user_id)
