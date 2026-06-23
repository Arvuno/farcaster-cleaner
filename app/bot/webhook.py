"""FastAPI webhook integration for Telegram."""

import hashlib
import hmac
import logging
from typing import Optional

from fastapi import Request, HTTPException
from telegram import Update

from app.config import get_settings

logger = logging.getLogger(__name__)


def _verify_telegram_hash(init_data: str, secret_key: str) -> bool:
    """Verify the HMAC-SHA256 signature of Telegram init data."""
    try:
        parsed = dict(x.split("=", 1) for x in init_data.split("&") if "=" in x)
        hash_field = parsed.get("hash", "")
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items()) if k != "hash"
        )
        secret = hmac.new(
            key=b"WebAppData",
            msg=secret_key.encode(),
            digestmod=hashlib.sha256
        ).digest()
        expected_hash = hmac.new(
            key=secret,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(hash_field, expected_hash)
    except Exception as e:
        logger.error(f"Telegram hash verification error: {e}")
        return False


async def telegram_webhook(request: Request) -> dict:
    """Process incoming Telegram webhook updates."""
    settings = get_settings()

    if not settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    secret = settings.TELEGRAM_WEBHOOK_SECRET
    body = await request.body()

    try:
        import json
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if "message" in data:
        from telegram import Update
        update = Update.de_json(data, None)
        user_id = None
        if update.effective_user:
            user_id = update.effective_user.id

        admin_ids = settings.TELEGRAM_ADMIN_USER_IDS or ""
        if admin_ids:
            try:
                authorized = [int(x.strip()) for x in admin_ids.split(",") if x.strip()]
                if user_id not in authorized:
                    logger.warning(f"Unauthorized webhook access from user {user_id}")
                    return {"ok": True, "status": "unauthorized"}
            except ValueError:
                pass

        logger.info(f"Processing webhook update from user {user_id}")
        return {"ok": True, "status": "processed"}

    return {"ok": True, "status": "no_message"}
