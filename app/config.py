"""
Centralised configuration.
All env vars are loaded here — nothing else imports os.environ directly.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
    ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
    DATABASE_URL: str = os.environ["DATABASE_URL"]
    WEB_BASE_URL: str = os.environ.get("WEB_BASE_URL", "https://hypatia-web.vercel.app")

    # Scheduler
    SCHEDULER_INTERVAL_MINUTES: int = 5

    # LLM
    LLM_MODEL: str = "anthropic/claude-3.5-haiku"
    LLM_MAX_TOKENS: int = 300

    # Timezones shown in onboarding buttons
    TIMEZONE_OPTIONS: list[str] = [
        "UTC",
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Europe/Zurich",
        "Europe/Moscow",
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "Asia/Dubai",
        "Asia/Karachi",
        "Asia/Kolkata",
        "Asia/Bangkok",
        "Asia/Singapore",
        "Asia/Tokyo",
        "Australia/Sydney",
        "Africa/Cairo",
        "Africa/Nairobi",
    ]

    # Reminder time options shown in onboarding buttons
    REMINDER_TIME_OPTIONS: list[str] = [
        "18:00", "19:00", "20:00", "21:00",
        "22:00", "23:00",
    ]


config = Config()
