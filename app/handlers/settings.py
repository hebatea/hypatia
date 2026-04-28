"""
Settings and utility commands:
  /streak   — show current streak
  /history  — last 5 check-ins
  /remind   — change reminder time
  /pause    — disable reminders
  /resume   — re-enable reminders
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.db.engine import get_session
from app.db import repository as repo
from app.handlers.keyboards import reminder_time_keyboard, timezone_keyboard
from app.handlers.states import IDLE, ONBOARDING_TIME, ONBOARDING_TZ

logger = logging.getLogger(__name__)


async def cmd_streak(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    async with get_session() as session:
        user = await repo.get_user(session, user_id)

    if not user:
        await update.message.reply_text("Use /start to get set up first.")
        return

    streak = user.streak_count
    if streak == 0:
        msg = "No streak yet — start with /checkin 🌱"
    elif streak == 1:
        msg = "🌱 Day 1. Every long streak starts here."
    else:
        msg = f"🔥 *{streak} day streak*\n\nKeep going."

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    async with get_session() as session:
        checkins = await repo.get_recent_checkins(session, user_id, limit=5)

    if not checkins:
        await update.message.reply_text(
            "No check-ins yet. Start with /checkin 📝"
        )
        return

    lines = ["*Your last check-ins:*\n"]
    for c in checkins:
        date_str = c.created_at.strftime("%d %b")
        lines.append(
            f"📅 *{date_str}*\n"
            f"  Challenge: {c.challenge[:60]}{'…' if len(c.challenge) > 60 else ''}\n"
            f"  Grateful: {c.gratitude[:60]}{'…' if len(c.gratitude) > 60 else ''}\n"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_remind(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lets the user change their reminder time."""
    user_id = update.effective_user.id

    async with get_session() as session:
        user = await repo.get_user(session, user_id)
        if not user:
            await update.message.reply_text("Use /start first.")
            return
        await repo.update_user_state(session, user_id, ONBOARDING_TIME)

    await update.message.reply_text(
        "What time would you like your daily reminder?",
        reply_markup=reminder_time_keyboard(),
    )


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    async with get_session() as session:
        await repo.update_user_settings(session, user_id, reminders_enabled=False)

    await update.message.reply_text(
        "Reminders paused ⏸\n\nUse /resume to turn them back on."
    )


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    async with get_session() as session:
        user = await repo.get_user(session, user_id)
        if not user or not user.reminder_time:
            await update.message.reply_text(
                "No reminder time set yet. Use /remind to set one."
            )
            return
        await repo.update_user_settings(session, user_id, reminders_enabled=True)

    time_str = user.reminder_time.strftime("%H:%M")
    await update.message.reply_text(
        f"Reminders back on ▶ I'll message you at {time_str} each day."
    )


async def callback_nav(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles nav:history and nav:streak inline buttons."""
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]

    # Reuse the command handlers but adapt for callback context
    if action == "history":
        user_id = query.from_user.id
        async with get_session() as session:
            checkins = await repo.get_recent_checkins(session, user_id, limit=5)

        if not checkins:
            await query.edit_message_text("No check-ins yet. Use /checkin to start.")
            return

        lines = ["*Your last check-ins:*\n"]
        for c in checkins:
            date_str = c.created_at.strftime("%d %b")
            lines.append(
                f"📅 *{date_str}*\n"
                f"  Challenge: {c.challenge[:60]}{'…' if len(c.challenge) > 60 else ''}\n"
            )
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")

    elif action == "streak":
        user_id = query.from_user.id
        async with get_session() as session:
            user = await repo.get_user(session, user_id)
        streak = user.streak_count if user else 0
        await query.edit_message_text(
            f"🔥 *{streak} day streak*", parse_mode="Markdown"
        )
