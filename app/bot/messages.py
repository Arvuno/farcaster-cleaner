"""Message formatters for the Telegram bot."""

from typing import List

from app.models import Cast, DeleteJob


def format_cast_list(casts: List[Cast], page: int = 1, per_page: int = 10) -> str:
    """Format a paginated list of casts."""
    if not casts:
        return "No casts found."

    total_pages = (len(casts) + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    page_casts = casts[start:end]

    lines = [f"Cast List (Page {page}/{total_pages}):\n"]
    for i, cast in enumerate(page_casts, start + 1):
        lines.append(format_cast_item(cast, i))

    if total_pages > 1:
        lines.append(f"\nPage {page} of {total_pages}. Use /fetch to restart.")
    return "\n".join(lines)


def format_cast_item(cast: Cast, index: int) -> str:
    """Format a single cast for display."""
    timestamp_str = ""
    if cast.timestamp:
        timestamp_str = f" [{cast.timestamp.strftime('%Y-%m-%d %H:%M')}]"

    kind_indicator = ""
    if cast.kind.value == "reply":
        kind_indicator = " [REPLY]"
    elif cast.kind.value == "recast":
        kind_indicator = " [RECAST]"

    text_preview = cast.text[:100] + ("..." if len(cast.text) > 100 else "")
    return (
        f"{index}. {cast.hash[:12]}...{timestamp_str}{kind_indicator}\n"
        f"   {text_preview}\n"
    )


def format_job_status(job: DeleteJob) -> str:
    """Format a delete job status for display."""
    status_emoji = {
        "prepared": "⏳",
        "running": "⚙️",
        "completed": "✅",
        "failed": "❌",
        "cancelled": "✕",
    }.get(job.status.value, "❓")

    lines = [
        f"Job Status {status_emoji}",
        f"ID: {job.id}",
        f"Status: {job.status.value.upper()}",
        f"Progress: {job.deleted}/{job.total} deleted",
    ]

    if job.failed > 0:
        lines.append(f"Failed: {job.failed}")
    if job.skipped > 0:
        lines.append(f"Skipped: {job.skipped}")

    if job.last_message:
        lines.append(f"Last: {job.last_message}")

    return "\n".join(lines)


def format_confirmation(job_id: str, count: int) -> str:
    """Format a delete confirmation prompt."""
    return (
        f"⚠️ *Delete Confirmation*\n\n"
        f"You are about to delete *{count}* cast(s).\n"
        f"Job ID: `{job_id}`\n\n"
        f"Reply with your confirmation phrase to proceed.\n"
        f"Or use the buttons below."
    )


def format_help() -> str:
    """Format the help message."""
    return (
        "*Farcaster Cleaner Bot*\n\n"
        "Manage and delete your casts easily.\n\n"
        "*Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/settings - Configure bot settings\n"
        "/fetch - Fetch your casts\n"
        "/cancel - Cancel current operation\n\n"
        "*Admin Commands:*\n"
        "/status - View system status\n"
        "/stats - View statistics\n"
        "/broadcast - Broadcast a message\n\n"
        "Use the inline buttons to navigate and confirm actions."
    )


def format_settings() -> str:
    """Format the settings display."""
    return (
        "*Bot Settings*\n\n"
        "Configure your preferences below.\n"
        "Use /fetch to fetch casts with current settings."
    )


def format_fetch_mode_select() -> str:
    """Format the fetch mode selection prompt."""
    return (
        "*Select Fetch Mode*\n\n"
        "Choose which casts to fetch:\n\n"
        "*All Casts* - Fetch all casts\n"
        "*Root Only* - Fetch only root-level casts\n"
        "*Replies Only* - Fetch only reply casts"
    )


def format_scan_summary(session_info: dict) -> str:
    """Format a scan session summary."""
    return (
        f"*Scan Complete*\n\n"
        f"Fetched: {session_info.get('fetched', 0)} casts\n"
        f"Selected: {session_info.get('selected', 0)} casts\n"
        f"Mode: {session_info.get('mode', 'unknown')}\n\n"
        f"Use the buttons below to select casts for deletion."
    )
