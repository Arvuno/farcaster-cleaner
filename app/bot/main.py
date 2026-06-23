"""Bot entrypoint with polling and webhook modes."""

import asyncio
import logging
import os
import signal
import sys
from typing import Optional

import telegram
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from app.config import (
    get_settings,
    assert_private_mode_safe,
    assert_webhook_mode_safe,
    TELEGRAM_BOT_TOKEN,
)

from app.bot.router import get_handlers, get_callback_handlers

logger = logging.getLogger(__name__)

try:
    from app.config import PublicModeUnsafe
except ImportError:
    PublicModeUnsafe = Exception


class BotRunner:
    """Manages bot lifecycle."""

    def __init__(self):
        self.app: Optional[Application] = None
        self.shutdown_event = asyncio.Event()

    def _setup_logging(self) -> None:
        """Configure logging."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )

    def _register_handlers(self, app: Application) -> None:
        """Register all command and callback handlers."""
        for command, handler in get_handlers():
            app.add_handler(CommandHandler(command, handler))

        for pattern, handler in get_callback_handlers():
            app.add_handler(CallbackQueryHandler(handler, pattern=pattern))

    async def _signal_handler(self) -> None:
        """Handle shutdown signals."""
        self.shutdown_event.set()

    def run_polling(self) -> None:
        """Run the bot in polling mode."""
        settings = get_settings()
        token = settings.TELEGRAM_BOT_TOKEN

        if not token:
            logger.error("TELEGRAM_BOT_TOKEN is not set")
            sys.exit(1)

        try:
            import python_telegram_bot as ptb
            logger.info(f"Using python-telegram-bot v{ptb.__version__}")
        except (ImportError, AttributeError):
            logger.info("Using python-telegram-bot (version unknown)")

        app = Application.builder().token(token).build()
        self._register_handlers(app)

        app.run_polling(
            allowed_updates=telegram.update.Update.ALL_TYPES,
            shutdown_hook=self._signal_handler,
        )

    def run_webhook(self) -> None:
        """Run the bot in webhook mode."""
        settings = get_settings()
        token = settings.TELEGRAM_BOT_TOKEN
        webhook_url = settings.PUBLIC_BASE_URL
        secret = settings.TELEGRAM_WEBHOOK_SECRET

        if not all([token, webhook_url, secret]):
            logger.error("Missing required settings for webhook mode")
            sys.exit(1)

        app = Application.builder().token(token).build()
        self._register_handlers(app)

        webhook_path = f"/telegram/webhook/{secret}"

        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8443)),
            url_path=secret,
            webhook_url=f"{webhook_url}{webhook_path}",
            shutdown_hook=self._signal_handler,
        )


def run_polling() -> None:
    """Entry point for polling mode."""
    runner = BotRunner()
    runner._setup_logging()

    try:
        runner.run_polling()
    except KeyboardInterrupt:
        logger.info("Polling stopped by user")


def run_webhook() -> None:
    """Entry point for webhook mode."""
    runner = BotRunner()
    runner._setup_logging()

    try:
        runner.run_webhook()
    except KeyboardInterrupt:
        logger.info("Webhook server stopped by user")


def main() -> None:
    """Choose and run the bot in the configured mode."""
    settings = get_settings()
    mode = settings.BOT_MODE.lower() if settings.BOT_MODE else "polling"

    if mode == "webhook":
        run_webhook()
    else:
        run_polling()


if __name__ == "__main__":
    main()
