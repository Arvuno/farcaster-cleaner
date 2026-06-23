"""FSM states for the Telegram bot."""

from enum import Enum


class BotStates(str, Enum):
    """Telegram bot FSM states."""

    IDLE = "idle"
    WAITING_FOR_SELECTION = "waiting_selection"
    WAITING_FOR_CONFIRM = "waiting_confirm"
    SELECTING_MODE = "selecting_mode"
