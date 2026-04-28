"""
Scheduler service.
Runs every N minutes, finds users due for a reminder,
calls LLM, sends the message, logs it.
"""
import logging
from datetime import datetime, timedelta

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from app.config import config
from app.db.engine import get_session
from app.db import repository as repo
from app.services.llm import generate_reminder

logger = logging.getLogger(__name__)


def _user_local_time(timezone_str: str) -> datetime:
    """Returns current datetime in the user's timezone."""
    tz = pytz.timezone(timezone_str)
    return datetime.now(tz)


def _is_due(reminder_time, timezone_str: str, window_minutes: int = 5) -> bool:
    """
    Returns True if the user's reminder_time falls within the next
    `window_minutes` from now, in their local timezone.
    """
    now = _user_local_time(timezone_str)
    now_time = now.time().replace(second=0, microsecond=0)

    # Build a window: [reminder_time, reminder_time + window_minutes)
    from datetime import time as dtime
    reminder_dt = datetime.combine(now.date(), reminder_time)
    window_end = reminder_dt + timedelta(minutes=window_minutes)
    now_dt = datetime.combine(now.date(), now_time)

    return reminder_dt <= now_dt < window_end


async def _run_reminder_job(bot: Bot) -> None:
    """Core reminder logic — called by the scheduler every interval."""
    async with get_session() as session:
        users = await repo.get_users_due_for_reminder(session)

    for user in users:
        try:
            # Check if due in their timezone
            if not _is_due(user.reminder_time, user.timezone):
                continue

            # Check if already checked in today (in their timezone)
            user_today = _user_local_time(user.timezone).date()
            async with get_session() as session:
                already_done = await repo.checked_in_today(
                    session, user.id, user_today
                )

            if already_done:
                logger.debug(f"User {user.id} already checked in — skipping reminder")
                continue

            # Generate personalised message
            day_name = _user_local_time(user.timezone).strftime("%A")
            message = await generate_reminder(
                first_name=user.first_name or "friend",
                streak=user.streak_count,
                timezone=user.timezone,
                day_of_week=day_name,
            )

            # Send via Telegram
            await bot.send_message(chat_id=user.id, text=message)
            logger.info(f"Reminder sent to user {user.id}")

            # Log it
            async with get_session() as session:
                await repo.log_reminder(session, user.id, message, status="sent")

        except Exception as e:
            logger.error(f"Reminder failed for user {user.id}: {e}")
            async with get_session() as session:
                await repo.log_reminder(session, user.id, None, status="failed")


def create_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    Creates and returns the scheduler.
    Call scheduler.start() after bot initialisation.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_reminder_job,
        trigger="interval",
        minutes=config.SCHEDULER_INTERVAL_MINUTES,
        kwargs={"bot": bot},
        id="reminder_job",
        replace_existing=True,
    )
    return scheduler
