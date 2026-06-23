"""Telegram user validation and authorization."""

import logging
from typing import Optional

from telegram import Update

from app.config import get_settings, is_admin_user

logger = logging.getLogger(__name__)


def get_telegram_user_id(update: Update) -> Optional[int]:
    """Extract the Telegram user ID from an update."""
    if update.effective_user:
        return update.effective_user.id
    if update.callback_query and update.callback_query.from_user:
        return update.callback_query.from_user.id
    return None


def validate_telegram_user(update: Update) -> bool:
    """Validate that the update comes from an authorized Telegram user."""
    user_id = get_telegram_user_id(update)
    if user_id is None:
        logger.warning("Could not extract user ID from update")
        return False

    if not is_authorized_user(user_id):
        logger.warning(f"Unauthorized user attempt: {user_id}")
        return False

    return True


def is_authorized_user(tg_user_id: int) -> bool:
    """Check if a Telegram user ID is authorized to use the bot."""
    settings = get_settings()

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not configured")
        return False

    admin_ids = settings.TELEGRAM_ADMIN_USER_IDS or ""
    if not admin_ids:
        logger.warning("TELEGRAM_ADMIN_USER_IDS is not set - no users authorized")
        return False

    try:
        authorized_ids = [int(x.strip()) for x in admin_ids.split(",") if x.strip()]
        return tg_user_id in authorized_ids
    except ValueError as e:
        logger.error(f"Invalid TELEGRAM_ADMIN_USER_IDS format: {e}")
        return False
