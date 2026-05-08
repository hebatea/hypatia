"""
Onboarding handler — /start command.
Collects timezone and reminder time via inline buttons.
"""
import logging
from datetime import time as dtime

from telegram import Update
from telegram.ext import ContextTypes

from app.db.engine import get_session
from app.db import repository as repo
from app.handlers.keyboards import reminder_time_keyboard, timezone_keyboard
from app.handlers.states import IDLE, ONBOARDING_TIME, ONBOARDING_TZ

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point. Creates user if new, starts onboarding or greets existing."""
    tg_user = update.effective_user

    async with get_session() as session:
        user, created = await repo.get_or_create_user(
            session,
            user_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
        )
        already_set_up = user.timezone is not None and user.reminder_time is not None

        if not created and already_set_up:
            await update.message.reply_text(
                f"Welcome back {tg_user.first_name} 🌿\n\n"
                "You're already set up. Your reminder is running "
                "and your journey is saved.\n\n"
                "Pick up where you left off:\n\n"
                "/checkin · Daily check-in\n"
                "/step1 · The Foundation of Honesty"
            )
            return

        # Start onboarding
        await repo.update_user_state(session, tg_user.id, ONBOARDING_TZ)

    await update.message.reply_text(
        "Welcome to Hypatia 🌿\n\n"
        "This is your private daily companion for recovery.\n\n"
        "A safe space to be honest — with yourself, about "
        "yourself. No judgment. No audience. Just you.\n\n"
        "Every evening I'll check in with you. Three simple "
        "questions. Two minutes. And over time, something shifts.\n\n"
        "🔒 Everything you share here is private. Only you "
        "can see your answers. Send /privacy anytime.\n\n"
        "But first — let's get you set up.\n\n"
        "What timezone are you in?",
        reply_markup=timezone_keyboard(),
    )


async def callback_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """User tapped a timezone button."""
    query = update.callback_query
    await query.answer()

    timezone = query.data.split(":", 1)[1]
    user_id = query.from_user.id

    async with get_session() as session:
        user = await repo.get_user(session, user_id)
        if not user or user.state != ONBOARDING_TZ:
            return

        await repo.update_user_settings(session, user_id, timezone=timezone)
        await repo.update_user_state(session, user_id, ONBOARDING_TIME)

    await query.edit_message_text(
        "Got it ✓\n\n"
        "What time should I check in with you each evening?\n\n"
        "Pick a time when the day is winding down and you "
        "have two quiet minutes.",
        reply_markup=reminder_time_keyboard(),
    )


async def callback_reminder_time(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """User tapped a reminder time button."""
    query = update.callback_query
    await query.answer()

    time_str = query.data.split(":", 1)[1]
    hour, minute = map(int, time_str.split(":"))
    reminder_time = dtime(hour, minute)
    user_id = query.from_user.id

    async with get_session() as session:
        user = await repo.get_user(session, user_id)
        if not user or user.state != ONBOARDING_TIME:
            return

        await repo.update_user_settings(
            session, user_id, reminder_time=reminder_time
        )
        await repo.update_user_state(session, user_id, IDLE)

    await query.edit_message_text(
        f"You're all set 🌱\n\n"
        f"I'll be here every evening at *{time_str}*.\n\n"
        "When you're ready — and there's no rush — your "
        "journey begins with:\n\n"
        "/step1 · The Foundation of Honesty\n\n"
        "This is the most important thing you'll do. "
        "Take your time. I'll be here.",
        parse_mode="Markdown",
    )
