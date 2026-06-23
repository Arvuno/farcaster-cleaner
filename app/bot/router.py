"""All bot handlers for the Telegram bot."""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards import (
    admin_keyboard,
    cast_selection_keyboard,
    confirmation_keyboard,
    mode_selection_keyboard,
    reply_keyboards,
)
from app.bot.messages import (
    format_cast_list,
    format_confirmation,
    format_fetch_mode_select,
    format_help,
    format_job_status,
    format_scan_summary,
    format_settings,
)
from app.bot.states import BotStates
from app.config import (
    get_settings,
    is_admin_user,
)
from app.models import Cast, DeleteJob, FetchMode, JobStatus

try:
    from app.services.scan_service import create_session, fetch_casts_for_session, ScanSession
except ImportError:
    ScanSession = None
    create_session = None
    fetch_casts_for_session = None

try:
    from app.services.deletion_service import prepare, confirm_and_start, cancel
except ImportError:
    prepare = None
    confirm_and_start = None
    cancel = None

logger = logging.getLogger(__name__)

BOT_STATES = {
    "user_states": {},
}


def get_user_state(user_id: int) -> BotStates:
    """Get the current FSM state for a user."""
    return BOT_STATES["user_states"].get(user_id, BotStates.IDLE)


def set_user_state(user_id: int, state: BotStates) -> None:
    """Set the FSM state for a user."""
    BOT_STATES["user_states"][user_id] = state


def clear_user_state(user_id: int) -> None:
    """Clear the FSM state for a user."""
    BOT_STATES["user_states"].pop(user_id, None)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return

    is_admin = is_admin_user(user_id)
    keyboard = reply_keyboards()

    greeting = (
        "Welcome to *Farcaster Cleaner Bot*!\n\n"
        "I help you manage and delete your casts.\n"
        "Use /help to see available commands."
    )

    if is_admin:
        greeting += "\n\n*Admin mode enabled.*"
        await update.message.reply_text(
            greeting,
            parse_mode="Markdown",
            reply_markup=keyboard["admin"]
        )
    else:
        await update.message.reply_text(
            greeting,
            parse_mode="Markdown",
            reply_markup=keyboard["main"]
        )

    clear_user_state(user_id)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(
        format_help(),
        parse_mode="Markdown",
        reply_markup=reply_keyboards()["main"]
    )


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings command."""
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return

    settings_obj = get_settings()
    lines = [
        "*Current Settings*\n",
        f"Delete Rate: {settings_obj.DELETE_RATE_LIMIT_RPS} casts/sec",
        f"Max Attempts: {settings_obj.DELETE_MAX_ATTEMPTS}",
        f"Default Mode: {settings_obj.DEFAULT_MODE}",
        f"Include Recasts: {settings_obj.INCLUDE_RECASTS}",
    ]

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=reply_keyboards()["main"]
    )


async def fetch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /fetch command - start fetching casts."""
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return

    await update.message.reply_text(
        format_fetch_mode_select(),
        parse_mode="Markdown",
        reply_markup=mode_selection_keyboard()
    )
    set_user_state(user_id, BotStates.SELECTING_MODE)


async def select_cast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle cast selection from fetched casts."""
    query = update.callback_query
    if not query:
        return

    user_id = query.from_user.id if query.from_user else None
    if not user_id:
        return

    data = query.data or ""

    if data == "mode:all":
        await query.answer("Fetching all casts...")
        await _fetch_casts(update, context, FetchMode.ALL)
    elif data == "mode:root_only":
        await query.answer("Fetching root casts only...")
        await _fetch_casts(update, context, FetchMode.ROOT_ONLY)
    elif data == "mode:replies_only":
        await query.answer("Fetching reply casts only...")
        await _fetch_casts(update, context, FetchMode.REPLIES_ONLY)
    elif data == "mode:cancel":
        await query.answer("Cancelled")
        await query.edit_message_text("Fetch cancelled. Use /fetch to start again.")
        clear_user_state(user_id)
    else:
        await query.answer("Unknown selection")


async def _fetch_casts(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: FetchMode) -> None:
    """Internal: fetch casts and show selection keyboard."""
    query = update.callback_query
    user_id = query.from_user.id if query.from_user else None
    if not user_id:
        return

    if create_session is None or fetch_casts_for_session is None:
        await query.edit_message_text(
            "Error: Scan service not available.",
            reply_markup=None
        )
        return

    try:
        settings_obj = get_settings()
        session = create_session(
            api_key=settings_obj.NEYNAR_API_KEY,
            signer_uuid=settings_obj.NEYNAR_SIGNER_UUID,
            fid=settings_obj.FARCASTER_FID,
        )

        casts = fetch_casts_for_session(session, mode=mode)

        if not casts:
            await query.edit_message_text(
                "No casts found for your account.",
                reply_markup=None
            )
            clear_user_state(user_id)
            return

        context.user_data["pending_casts"] = casts
        await query.edit_message_text(
            format_cast_list(casts, page=1),
            reply_markup=cast_selection_keyboard(casts),
            parse_mode="Markdown"
        )
        set_user_state(user_id, BotStates.WAITING_FOR_SELECTION)

    except Exception as e:
        logger.error(f"Error fetching casts: {e}")
        await query.edit_message_text(
            f"Error fetching casts: {str(e)}",
            reply_markup=None
        )
        clear_user_state(user_id)


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle delete confirmation."""
    query = update.callback_query
    if not query:
        return

    user_id = query.from_user.id if query.from_user else None
    if not user_id:
        return

    data = query.data or ""

    if data.startswith("delete_confirm:"):
        job_id = data.split(":", 1)[1]
        await query.answer("Deletion started!")
        await query.edit_message_text(
            f"Deletion job `{job_id}` has been started.\n"
            "Use /status to monitor progress.",
            parse_mode="Markdown"
        )
        clear_user_state(user_id)

    elif data.startswith("delete_cancel:"):
        job_id = data.split(":", 1)[1]
        if cancel is not None:
            try:
                cancel(job_id)
                await query.answer("Job cancelled")
            except Exception as e:
                logger.error(f"Error cancelling job {job_id}: {e}")
        await query.edit_message_text("Deletion cancelled.")
        clear_user_state(user_id)

    else:
        await query.answer("Unknown action")


async def cancel_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command."""
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return

    current_state = get_user_state(user_id)
    if current_state == BotStates.IDLE:
        await update.message.reply_text("Nothing to cancel.")
        return

    clear_user_state(user_id)
    await update.message.reply_text("Operation cancelled.")
    await help_command(update, context)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin: Handle /status command."""
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id or not is_admin_user(user_id):
        await update.message.reply_text("Unauthorized.")
        return

    from app.db.database import get_db
    from app.models import DeleteJob

    try:
        db = get_db()
        recent_jobs = db.query(DeleteJob).order_by(DeleteJob.created_at.desc()).limit(5).all()

        if not recent_jobs:
            await update.message.reply_text(
                "No delete jobs found.",
                reply_markup=admin_keyboard()
            )
            return

        lines = ["*Recent Delete Jobs*\n"]
        for job in recent_jobs:
            lines.append(format_job_status(job))
            lines.append("---")

        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=admin_keyboard()
        )

    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        await update.message.reply_text(
            f"Error fetching status: {str(e)}",
            reply_markup=admin_keyboard()
        )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin: Handle /stats command."""
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id or not is_admin_user(user_id):
        await update.message.reply_text("Unauthorized.")
        return

    await update.message.reply_text(
        "*Statistics*\n\n"
        "Use /status for job details.\n"
        "Use /broadcast to send messages to users.",
        parse_mode="Markdown",
        reply_markup=admin_keyboard()
    )


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin: Handle /broadcast command."""
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id or not is_admin_user(user_id):
        await update.message.reply_text("Unauthorized.")
        return

    if context.args:
        message = " ".join(context.args)
        await update.message.reply_text(
            f"Broadcast feature coming soon.\n"
            f"Message: {message}",
            reply_markup=admin_keyboard()
        )
    else:
        await update.message.reply_text(
            "Usage: /broadcast <message>",
            reply_markup=admin_keyboard()
        )


def get_handlers() -> list:
    """Return all bot handlers for registration."""
    return [
        ("start", start),
        ("help", help_command),
        ("settings", settings),
        ("fetch", fetch),
        ("cancel", cancel_delete),
        ("status", status),
        ("stats", stats),
        ("broadcast", broadcast),
    ]


def get_callback_handlers() -> list:
    """Return all callback query handlers."""
    return [
        ("", select_cast),
        ("", confirm_delete),
    ]
