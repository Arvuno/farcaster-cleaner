"""Inline and reply keyboards for the Telegram bot."""

from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.models import Cast


def cast_selection_keyboard(casts: List[Cast]) -> InlineKeyboardMarkup:
    """Build an inline keyboard for cast selection with select-all and confirm buttons."""
    keyboard: List[List[InlineKeyboardButton]] = []

    for cast in casts:
        display_text = cast.text[:60] + ("..." if len(cast.text) > 60 else "")
        keyboard.append([
            InlineKeyboardButton(
                text=f"[{cast.hash[:8]}] {display_text}",
                callback_data=f"cast_select:{cast.hash}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="Select All", callback_data="cast_select:all"),
        InlineKeyboardButton(text="Confirm Selection", callback_data="cast_confirm:ready"),
    ])
    keyboard.append([
        InlineKeyboardButton(text="Cancel", callback_data="cast_cancel"),
    ])

    return InlineKeyboardMarkup(keyboard)


def confirmation_keyboard(job_id: str) -> InlineKeyboardMarkup:
    """Build a confirmation keyboard for delete operation."""
    keyboard = [
        [
            InlineKeyboardButton(
                text="Confirm Delete",
                callback_data=f"delete_confirm:{job_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="Cancel",
                callback_data=f"delete_cancel:{job_id}"
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_keyboard() -> InlineKeyboardMarkup:
    """Build an inline keyboard for admin commands."""
    keyboard = [
        [
            InlineKeyboardButton(text="Status", callback_data="admin:status"),
            InlineKeyboardButton(text="Stats", callback_data="admin:stats"),
        ],
        [
            InlineKeyboardButton(text="Broadcast", callback_data="admin:broadcast"),
            InlineKeyboardButton(text="Back", callback_data="admin:back"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def mode_selection_keyboard() -> InlineKeyboardMarkup:
    """Build an inline keyboard for fetch mode selection."""
    keyboard = [
        [
            InlineKeyboardButton(text="All Casts", callback_data="mode:all"),
            InlineKeyboardButton(text="Root Only", callback_data="mode:root_only"),
        ],
        [
            InlineKeyboardButton(text="Replies Only", callback_data="mode:replies_only"),
        ],
        [
            InlineKeyboardButton(text="Cancel", callback_data="mode:cancel"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def reply_keyboards() -> dict:
    """Return a dictionary of reply keyboards (for ReplyKeyboardMarkup)."""
    from telegram import KeyboardButton, ReplyKeyboardMarkup

    main_keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton(text="/start")],
            [KeyboardButton(text="/help")],
            [KeyboardButton(text="/settings")],
            [KeyboardButton(text="/fetch")],
        ],
        resize_keyboard=True,
    )

    admin_keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton(text="/start")],
            [KeyboardButton(text="/help")],
            [KeyboardButton(text="/status")],
            [KeyboardButton(text="/stats")],
        ],
        resize_keyboard=True,
    )

    return {"main": main_keyboard, "admin": admin_keyboard}
