"""
Repository layer — all database queries live here.
Handlers and services never write raw SQL; they call these functions.
"""
import secrets
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from sqlalchemy import select, desc, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Checkin, MagicLink, ReminderLog, StepEntry, User


# ─── USER ──────────────────────────────────────────────────────────────────


async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    result = await session.get(User, user_id)
    return result


async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> tuple[User, bool]:
    """Returns (user, created). created=True if this is a new user."""
    user = await session.get(User, user_id)
    if user:
        return user, False

    user = User(id=user_id, username=username, first_name=first_name)
    session.add(user)
    await session.flush()
    return user, True


async def update_user_state(
    session: AsyncSession,
    user_id: int,
    state: str,
    current_step: int = 0,
) -> None:
    user = await session.get(User, user_id)
    if user:
        user.state = state
        user.current_step = current_step


async def update_user_temp(
    session: AsyncSession,
    user_id: int,
    challenge: Optional[str] = None,
    gratitude: Optional[str] = None,
) -> None:
    user = await session.get(User, user_id)
    if not user:
        return
    if challenge is not None:
        user.temp_challenge = challenge
    if gratitude is not None:
        user.temp_gratitude = gratitude


async def update_user_settings(
    session: AsyncSession,
    user_id: int,
    timezone: Optional[str] = None,
    reminder_time: Optional[time] = None,
    reminders_enabled: Optional[bool] = None,
) -> None:
    user = await session.get(User, user_id)
    if not user:
        return
    if timezone is not None:
        user.timezone = timezone
    if reminder_time is not None:
        user.reminder_time = reminder_time
    if reminders_enabled is not None:
        user.reminders_enabled = reminders_enabled


async def update_streak(
    session: AsyncSession,
    user_id: int,
    today: date,
) -> int:
    """
    Recalculates streak based on last_checkin_date.
    Returns the new streak count.
    """
    from datetime import timedelta

    user = await session.get(User, user_id)
    if not user:
        return 0

    yesterday = today - timedelta(days=1)

    if user.last_checkin_date == yesterday:
        user.streak_count += 1
    elif user.last_checkin_date == today:
        pass  # duplicate guard — don't change streak
    else:
        user.streak_count = 1

    user.last_checkin_date = today
    return user.streak_count


async def get_users_due_for_reminder(session: AsyncSession) -> list[User]:
    """
    Returns users whose reminder should fire right now.
    Called by scheduler every 5 minutes.
    Filtering by time window happens in the service layer
    to keep timezone logic out of SQL.
    """
    result = await session.execute(
        select(User).where(
            User.reminders_enabled == True,
            User.reminder_time.isnot(None),
            User.timezone.isnot(None),
        )
    )
    return list(result.scalars().all())


# ─── CHECKIN ───────────────────────────────────────────────────────────────


async def checked_in_today(
    session: AsyncSession,
    user_id: int,
    today: date,
) -> bool:
    user = await session.get(User, user_id)
    if not user:
        return False
    return user.last_checkin_date == today


async def save_checkin(
    session: AsyncSession,
    user_id: int,
    challenge: str,
    gratitude: str,
    intention: str,
    llm_response: Optional[str],
    streak: int,
) -> Checkin:
    checkin = Checkin(
        user_id=user_id,
        challenge=challenge,
        gratitude=gratitude,
        intention=intention,
        llm_response=llm_response,
        streak_at_time=streak,
    )
    session.add(checkin)
    await session.flush()
    return checkin


async def get_recent_checkins(
    session: AsyncSession,
    user_id: int,
    limit: int = 5,
) -> list[Checkin]:
    result = await session.execute(
        select(Checkin)
        .where(Checkin.user_id == user_id)
        .order_by(desc(Checkin.created_at))
        .limit(limit)
    )
    return list(result.scalars().all())


# ─── REMINDER LOG ──────────────────────────────────────────────────────────


async def log_reminder(
    session: AsyncSession,
    user_id: int,
    message: Optional[str],
    status: str = "sent",
) -> None:
    entry = ReminderLog(user_id=user_id, message_sent=message, status=status)
    session.add(entry)


# ─── MAGIC LINKS ───────────────────────────────────────────────────────────


async def create_magic_link(session: AsyncSession, user_id: int) -> str:
    """Creates a new magic link token valid for 24 hours. Returns the token."""
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    link = MagicLink(
        user_id=user_id,
        token=token,
        created_at=now,
        expires_at=now + timedelta(hours=24),
        used=False,
    )
    session.add(link)
    await session.flush()
    return token


# ─── STEP ENTRIES ──────────────────────────────────────────────────────────


async def save_step_answer(
    session: AsyncSession,
    user_id: int,
    step_number: int,
    question_number: int,
    answer: str,
) -> StepEntry:
    entry = StepEntry(
        user_id=user_id,
        step_number=step_number,
        question_number=question_number,
        answer=answer,
    )
    session.add(entry)
    await session.flush()
    return entry


async def get_step_answers(
    session: AsyncSession,
    user_id: int,
    step_number: int,
) -> list[StepEntry]:
    result = await session.execute(
        select(StepEntry)
        .where(StepEntry.user_id == user_id, StepEntry.step_number == step_number)
        .order_by(StepEntry.question_number)
    )
    return list(result.scalars().all())


# Maps step_number → total questions in that step
_STEP_QUESTION_COUNTS = {1: 4, 2: 3, 3: 3}


async def has_completed_step(
    session: AsyncSession,
    user_id: int,
    step_number: int,
) -> bool:
    entries = await get_step_answers(session, user_id, step_number)
    required = _STEP_QUESTION_COUNTS.get(step_number, 0)
    answered = {e.question_number for e in entries}
    return all(q in answered for q in range(1, required + 1))


async def delete_step_answers(
    session: AsyncSession,
    user_id: int,
    step_number: int,
) -> None:
    entries = await get_step_answers(session, user_id, step_number)
    for entry in entries:
        await session.delete(entry)
    await session.flush()


# ─── USER DELETION ─────────────────────────────────────────────────────────


async def delete_all_user_data(session: AsyncSession, user_id: int) -> None:
    """
    Permanently deletes all data for a user.
    Order respects FK constraints: child tables first, users row last.
    """
    await session.execute(sql_delete(MagicLink).where(MagicLink.user_id == user_id))
    await session.execute(sql_delete(ReminderLog).where(ReminderLog.user_id == user_id))
    await session.execute(sql_delete(StepEntry).where(StepEntry.user_id == user_id))
    await session.execute(sql_delete(Checkin).where(Checkin.user_id == user_id))
    user = await session.get(User, user_id)
    if user:
        await session.delete(user)
    await session.flush()


async def validate_token(session: AsyncSession, token: str) -> Optional[int]:
    """
    Returns the user_id if the token exists and has not expired.
    Token stays valid for its full 24-hour window and can be used multiple times.
    """
    result = await session.execute(
        select(MagicLink).where(MagicLink.token == token)
    )
    link = result.scalar_one_or_none()

    if not link:
        return None

    now = datetime.now(timezone.utc)
    expires = link.expires_at
    # Handle naive datetimes stored by SQLite (no tzinfo)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if now > expires:
        return None

    return link.user_id
