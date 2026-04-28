"""
LLM service — all Anthropic API calls live here.
Two public functions:
  - generate_reflection(answers) → post-checkin response
  - generate_reminder(user)      → personalised evening nudge
"""
import logging
from dataclasses import dataclass

import anthropic

from app.config import config

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

FALLBACK_REFLECTION = (
    "Thank you for showing up today. That matters more than you know. "
    "See you tomorrow. 🌿"
)

FALLBACK_REMINDER = (
    "Hey — time to check in with yourself. How was today? /checkin"
)


@dataclass
class CheckinAnswers:
    challenge: str
    gratitude: str
    intention: str
    streak: int
    first_name: str = "friend"


async def generate_reflection(answers: CheckinAnswers) -> str:
    """
    Reads all 3 checkin answers and returns a warm, personal 2-3 sentence reflection.
    Called after the user submits their third answer.
    """
    system_prompt = """You are Hypatia, a warm and grounded daily companion for people in 12-step recovery.

Your role: After a user completes their daily check-in, write a brief, personal response (2-3 sentences maximum).

Rules you MUST follow:
- Reference at least one thing the user actually wrote — do not be generic
- Be warm, calm, and non-judgmental — like a steady friend, not a therapist
- Never give advice, diagnose, or suggest professional help unless the user expresses crisis
- Never be preachy or quote 12-step literature
- Keep it under 60 words
- End with one encouraging sentence that feels human, not motivational-poster
- If the streak is 7, 14, 21, 30, 60, or 90 days — acknowledge it briefly"""

    user_message = f"""The user {answers.first_name} just completed their daily check-in.

Their answers:
- Challenge today: {answers.challenge}
- Grateful for: {answers.gratitude}
- Intention for tomorrow: {answers.intention}
- Current streak: {answers.streak} day(s)

Write their reflection now."""

    try:
        response = _client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=config.LLM_MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        text = response.content[0].text.strip()
        return text
    except Exception as e:
        logger.error(f"LLM reflection failed: {e}")
        return FALLBACK_REFLECTION


async def generate_reminder(
    first_name: str,
    streak: int,
    timezone: str,
    day_of_week: str,
) -> str:
    """
    Generates a personalised, varied evening reminder message.
    Called by the scheduler before sending the push notification.
    """
    system_prompt = """You are Hypatia, a warm daily companion for people in 12-step recovery.

Your role: Write a single short reminder message (1-2 sentences) to nudge the user to do their daily check-in.

Rules you MUST follow:
- The message must feel personal and vary — never the same twice
- Be gentle, not urgent or pushy
- Reference the day of the week or the streak only if it feels natural
- Never be preachy or robotic
- End with /checkin on a new line so the user can tap it immediately
- Total length: under 30 words before the /checkin"""

    user_message = f"""Write a reminder for {first_name}.
Streak: {streak} day(s).
Day: {day_of_week}.
Timezone: {timezone}.

Write the reminder now."""

    try:
        response = _client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=100,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        text = response.content[0].text.strip()
        # Ensure /checkin is always at the end
        if "/checkin" not in text:
            text += "\n\n/checkin"
        return text
    except Exception as e:
        logger.error(f"LLM reminder failed: {e}")
        return FALLBACK_REMINDER
