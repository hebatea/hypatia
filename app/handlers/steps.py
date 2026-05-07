"""
Steps handler — 12-step program flows.

Currently implements Step 1 (/step1).

State machine for Step 1:
  IDLE ──/step1──> IN_STEP1_Q1 ──answer──> IN_STEP1_Q2
       ──answer──> IN_STEP1_Q3 ──answer──> IN_STEP1_Q4
       ──answer──> LLM reflection ──> IDLE
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.db.engine import get_session
from app.db import repository as repo
from app.handlers.keyboards import step_redo_keyboard
from app.handlers.states import (
    IDLE,
    IN_STEP1_Q1, IN_STEP1_Q2, IN_STEP1_Q3, IN_STEP1_Q4,
)
from app.services.llm import generate_step_reflection

logger = logging.getLogger(__name__)

# ─── Step 1 content ────────────────────────────────────────────────────────

STEP1_INTRO = (
    "Before we begin Step 1, take a deep breath. This is the most "
    "important step you will ever take. We aren't here to judge you; "
    "we are here to help you see the truth.\n\n"
    "In this section, we are going to look at the Evidence. We want "
    "to prove to that voice in your head that you can stop, but you "
    "can't stay stopped on your own. Honesty is your only way out. "
    "Are you ready to look at the facts?"
)

STEP1_QUESTIONS = {
    1: (
        "Think of a time you promised yourself you'd only have one "
        "or just a little. What actually happened?"
    ),
    2: (
        "When you aren't using, does your mind try to trick you into "
        "thinking it will be different this time? Give a specific example."
    ),
    3: (
        "What are three things you have lost or damaged because of "
        "your addiction? For example: a job, a relationship, your "
        "self-respect."
    ),
    4: (
        "Looking at these answers, do you truly believe you can "
        "control this on your own? Yes or No."
    ),
}

# State → next state mapping for step 1
_STEP1_TRANSITIONS = {
    IN_STEP1_Q1: (1, IN_STEP1_Q2, 2),
    IN_STEP1_Q2: (2, IN_STEP1_Q3, 3),
    IN_STEP1_Q3: (3, IN_STEP1_Q4, 4),
    IN_STEP1_Q4: (4, None, None),  # final question
}

_STEP1_STATES = set(_STEP1_TRANSITIONS.keys())


# ─── Command handlers ───────────────────────────────────────────────────────


async def cmd_step1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    async with get_session() as session:
        user = await repo.get_user(session, user_id)

        if not user:
            await update.message.reply_text("Let's get you set up first. Use /start 👋")
            return

        if user.state != IDLE:
            await update.message.reply_text(
                "You're in the middle of something else. "
                "Finish or cancel that first."
            )
            return

        completed = await repo.has_completed_step(session, user_id, step_number=1)

        if completed:
            entries = await repo.get_step_answers(session, user_id, step_number=1)
            summary = _format_answers(entries)
            await update.message.reply_text(
                f"You've already completed Step 1 ✓\n\n{summary}",
                reply_markup=step_redo_keyboard(1),
                parse_mode="Markdown",
            )
            return

        await repo.update_user_state(session, user_id, IN_STEP1_Q1)

    await update.message.reply_text(STEP1_INTRO)
    await update.message.reply_text(
        f"*Q1:* {STEP1_QUESTIONS[1]}", parse_mode="Markdown"
    )


# ─── Message router ─────────────────────────────────────────────────────────


async def handle_step_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Routes free-text answers through the active step flow."""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    async with get_session() as session:
        user = await repo.get_user(session, user_id)
        if not user or user.state not in _STEP1_STATES:
            return

        state = user.state
        first_name = user.first_name or "friend"

    await _process_step1_answer(update, user_id, state, text, first_name)


async def _process_step1_answer(
    update: Update,
    user_id: int,
    state: str,
    text: str,
    first_name: str,
) -> None:
    q_num, next_state, next_q_num = _STEP1_TRANSITIONS[state]

    async with get_session() as session:
        await repo.save_step_answer(session, user_id, step_number=1,
                                    question_number=q_num, answer=text)

        if next_state is not None:
            await repo.update_user_state(session, user_id, next_state)

        if next_state is not None:
            await update.message.reply_text(
                f"Got it ✓\n\n*Q{next_q_num}:* {STEP1_QUESTIONS[next_q_num]}",
                parse_mode="Markdown",
            )
            return

        # Final answer — fetch all answers for reflection, then reset state
        entries = await repo.get_step_answers(session, user_id, step_number=1)
        answers = {e.question_number: e.answer for e in entries}
        await repo.update_user_state(session, user_id, IDLE)

    await update.message.reply_text("Thank you for your honesty. Reflecting… ✨")
    reflection = await generate_step_reflection(
        step_number=1, answers=answers, first_name=first_name
    )
    await update.message.reply_text(reflection)


# ─── Voice handler ───────────────────────────────────────────────────────────


async def handle_step_voice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Transcribes voice messages during step flows and routes them as text."""
    from app.services.transcription import transcribe_voice

    user_id = update.effective_user.id

    async with get_session() as session:
        user = await repo.get_user(session, user_id)
        if not user or user.state not in _STEP1_STATES:
            return

        state = user.state
        first_name = user.first_name or "friend"

    voice = update.message.voice
    tg_file = await context.bot.get_file(voice.file_id)
    file_bytes = bytes(await tg_file.download_as_bytearray())

    text = await transcribe_voice(file_bytes)
    if not text:
        await update.message.reply_text(
            "Sorry, I couldn't catch that. Please type instead."
        )
        return

    await update.message.reply_text(
        f"🎙️ I heard: _{text}_", parse_mode="Markdown"
    )
    await _process_step1_answer(update, user_id, state, text, first_name)


# ─── Callback handler ────────────────────────────────────────────────────────


async def callback_step(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles step:review:{n} and step:restart:{n} callbacks."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")   # ["step", "review"/"restart", "1"]
    if len(parts) != 3:
        return

    action = parts[1]
    try:
        step_number = int(parts[2])
    except ValueError:
        return

    user_id = query.from_user.id

    if action == "review":
        async with get_session() as session:
            entries = await repo.get_step_answers(session, user_id, step_number)

        if not entries:
            await query.edit_message_text("No answers found for that step.")
            return

        summary = _format_answers(entries)
        await query.edit_message_text(
            f"*Step {step_number} — your answers:*\n\n{summary}",
            parse_mode="Markdown",
        )

    elif action == "restart":
        async with get_session() as session:
            await repo.delete_step_answers(session, user_id, step_number)
            await repo.update_user_state(session, user_id, IN_STEP1_Q1)

        await query.edit_message_text(
            "Starting Step 1 over. Take your time. 🌱"
        )
        await query.message.reply_text(STEP1_INTRO)
        await query.message.reply_text(
            f"*Q1:* {STEP1_QUESTIONS[1]}", parse_mode="Markdown"
        )


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _format_answers(entries) -> str:
    lines = []
    for entry in sorted(entries, key=lambda e: e.question_number):
        q_text = STEP1_QUESTIONS.get(entry.question_number, f"Q{entry.question_number}")
        lines.append(f"*Q{entry.question_number}:* {q_text}\n_{entry.answer}_")
    return "\n\n".join(lines)
