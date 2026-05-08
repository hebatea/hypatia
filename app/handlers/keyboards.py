"""
Keyboard factory functions.
Every inline keyboard the bot uses is built here.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import config


def timezone_keyboard() -> InlineKeyboardMarkup:
    """Two-column grid of timezone buttons."""
    zones = config.TIMEZONE_OPTIONS
    rows = []
    for i in range(0, len(zones), 2):
        row = [InlineKeyboardButton(zones[i], callback_data=f"tz:{zones[i]}")]
        if i + 1 < len(zones):
            row.append(InlineKeyboardButton(zones[i + 1], callback_data=f"tz:{zones[i + 1]}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def reminder_time_keyboard() -> InlineKeyboardMarkup:
    """Row of reminder time buttons."""
    times = config.REMINDER_TIME_OPTIONS
    rows = []
    for i in range(0, len(times), 3):
        row = [
            InlineKeyboardButton(t, callback_data=f"rt:{t}")
            for t in times[i:i + 3]
        ]
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def checkin_resume_keyboard() -> InlineKeyboardMarkup:
    """Shown when user tries to start a new checkin mid-flow."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("▶ Resume", callback_data="checkin:resume"),
        InlineKeyboardButton("✕ Cancel", callback_data="checkin:cancel"),
    ]])


def step_redo_keyboard(step_number: int) -> InlineKeyboardMarkup:
    """Shown when a user has already completed a step."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📖 Review", callback_data=f"step:review:{step_number}"),
        InlineKeyboardButton("🔄 Start over", callback_data=f"step:restart:{step_number}"),
    ]])


def delete_confirm_keyboard() -> InlineKeyboardMarkup:
    """Shown when user requests /deletedata — requires explicit confirmation."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑 Yes, delete everything", callback_data="delete:confirm"),
        InlineKeyboardButton("← Cancel", callback_data="delete:cancel"),
    ]])


def already_done_keyboard() -> InlineKeyboardMarkup:
    """Shown when user has already checked in today."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📖 View history", callback_data="nav:history"),
        InlineKeyboardButton("🔥 My streak", callback_data="nav:streak"),
    ]])
