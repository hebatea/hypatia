"""
Check-in handler — the core daily flow.

State machine:
  IDLE ──/checkin──> IN_CHECKIN_1 ──answer──> IN_CHECKIN_2
       ──answer──> IN_CHECKIN_3 ──answer──> AWAITING_LLM ──llm──> IDLE
"""
import logging
from datetime import timezone as dt_timezone

import pytz
from telegram import Update
from telegram.ext import ContextTypes

from app.db.engine import get_session
from app.db import repository as repo
from app.handlers.keyboards import already_done_keyboard, checkin_resume_keyboard
from app.handlers.states import (
    AWAITING_LLM, IDLE, IN_CHECKIN_1, IN_CHECKIN_2, IN_CHECKIN_3, ONBOARDING_TZ,
)
from app.services.llm import CheckinAnswers, generate_reflection

logger = logging.getLogger(__name__)

Q1 = "What was your biggest challenge today?"
Q2 = "What are you grateful for today?"
Q3 = "What's one intention or goal for tomorrow?"


async def cmd_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for /checkin command."""
    user_id = update.effective_user.id

    async with get_session() as session:
        user = await repo.get_user(session, user_id)

        # Not set up yet
        if not user or not user.timezone:
            await update.message.reply_text(
                "Let's get you set up first. Use /start 👋"
            )
            return

        # Already in a checkin flow — offer resume or cancel
        if user.state in (IN_CHECKIN_1, IN_CHECKIN_2, IN_CHECKIN_3):
            await update.message.reply_text(
                "You're already in a check-in. Want to resume or start over?",
                reply_markup=checkin_resume_keyboard(),
            )
            return

        # Already checked in today
        user_tz = pytz.timezone(user.timezone)
        today = _today_for_user(user.timezone)
        already_done = await repo.checked_in_today(session, user_id, today)

        if already_done:
            await update.message.reply_text(
                f"You already checked in today 🌿 Streak: {user.streak_count} day(s)\n\n"
                "Come back tomorrow or browse your history.",
                reply_markup=already_done_keyboard(),
            )
            return

        # Start the flow
        await repo.update_user_state(session, user_id, IN_CHECKIN_1, current_step=1)

    await update.message.reply_text(
        f"Let's do it 📝\n\n*{Q1}*",
        parse_mode="Markdown",
    )


async def handle_checkin_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Routes free-text messages based on the user's current state.
    Called for every non-command message.
    """
    user_id = update.effective_user.id
    text = update.message.text.strip()

    async with get_session() as session:
        user = await repo.get_user(session, user_id)
        if not user:
            return

        state = user.state

        # ── Step 1: received challenge ──────────────────────────────────────
        if state == IN_CHECKIN_1:
            await repo.update_user_temp(session, user_id, challenge=text)
            await repo.update_user_state(session, user_id, IN_CHECKIN_2, current_step=2)
            await update.message.reply_text(
                f"Got it ✓\n\n*{Q2}*", parse_mode="Markdown"
            )

        # ── Step 2: received gratitude ──────────────────────────────────────
        elif state == IN_CHECKIN_2:
            await repo.update_user_temp(session, user_id, gratitude=text)
            await repo.update_user_state(session, user_id, IN_CHECKIN_3, current_step=3)
            await update.message.reply_text(
                f"Beautiful ✓\n\n*{Q3}*", parse_mode="Markdown"
            )

        # ── Step 3: received intention — save & call LLM ───────────────────
        elif state == IN_CHECKIN_3:
            await repo.update_user_state(session, user_id, AWAITING_LLM)

            challenge = user.temp_challenge or ""
            gratitude = user.temp_gratitude or ""
            intention = text
            first_name = user.first_name or "friend"

            # Update streak
            today = _today_for_user(user.timezone)
            streak = await repo.update_streak(session, user_id, today)

        else:
            return  # Not in a checkin flow — ignore

    # Outside session — call LLM (can be slow, don't hold DB connection)
    if state == IN_CHECKIN_3:
        await update.message.reply_text("Saving your check-in… ✨")

        answers = CheckinAnswers(
            challenge=challenge,
            gratitude=gratitude,
            intention=intention,
            streak=streak,
            first_name=first_name,
        )
        reflection = await generate_reflection(answers)

        # Save checkin + reflection + reset state
        async with get_session() as session:
            await repo.save_checkin(
                session,
                user_id=user_id,
                challenge=challenge,
                gratitude=gratitude,
                intention=intention,
                llm_response=reflection,
                streak=streak,
            )
            await repo.update_user_state(session, user_id, IDLE)
            # Clear temp fields
            await repo.update_user_temp(session, user_id, challenge=None, gratitude=None)

        streak_line = _streak_message(streak)
        await update.message.reply_text(
            f"{reflection}\n\n{streak_line}",
            parse_mode="Markdown",
        )


async def callback_checkin_flow(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles resume/cancel buttons shown mid-flow."""
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]
    user_id = query.from_user.id

    if action == "resume":
        async with get_session() as session:
            user = await repo.get_user(session, user_id)
            if not user:
                return
            step_map = {IN_CHECKIN_1: Q1, IN_CHECKIN_2: Q2, IN_CHECKIN_3: Q3}
            question = step_map.get(user.state, Q1)

        await query.edit_message_text(
            f"Resuming ▶\n\n*{question}*", parse_mode="Markdown"
        )

    elif action == "cancel":
        async with get_session() as session:
            await repo.update_user_state(session, user_id, IDLE, current_step=0)
            await repo.update_user_temp(session, user_id, challenge=None, gratitude=None)

        await query.edit_message_text(
            "Check-in cancelled. Use /checkin whenever you're ready."
        )


# ─── Helpers ───────────────────────────────────────────────────────────────

def _today_for_user(timezone_str: str):
    """Returns today's date in the user's local timezone."""
    from datetime import datetime
    tz = pytz.timezone(timezone_str)
    return datetime.now(tz).date()


def _streak_message(streak: int) -> str:
    milestones = {1: "Day 1. The hardest one. 🌱",
                  7: "7 days. One full week. 🔥",
                  14: "14 days straight. You're building something real. 💪",
                  21: "21 days. This is becoming a habit. ⚡",
                  30: "30 days. One month. That's extraordinary. 🏆",
                  60: "60 days. 🌟",
                  90: "90 days. 🎯"}
    if streak in milestones:
        return milestones[streak]
    return f"🔥 *{streak} day streak*"
