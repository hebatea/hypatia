"""
Bot factory.
Creates the Application, registers all handlers, returns it.
Nothing else should import from telegram.ext directly.
"""
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.config import config
from app.handlers.checkin import (
    callback_checkin_flow,
    cmd_checkin,
    handle_checkin_message,
)
from app.handlers.onboarding import (
    callback_reminder_time,
    callback_timezone,
    cmd_start,
)
from app.handlers.settings import (
    callback_nav,
    cmd_history,
    cmd_pause,
    cmd_remind,
    cmd_resume,
    cmd_streak,
)


def create_bot() -> Application:
    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .build()
    )

    # ── Commands ──────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("checkin", cmd_checkin))
    app.add_handler(CommandHandler("streak", cmd_streak))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("remind", cmd_remind))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))

    # ── Callback queries ──────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(callback_timezone, pattern=r"^tz:"))
    app.add_handler(CallbackQueryHandler(callback_reminder_time, pattern=r"^rt:"))
    app.add_handler(CallbackQueryHandler(callback_checkin_flow, pattern=r"^checkin:"))
    app.add_handler(CallbackQueryHandler(callback_nav, pattern=r"^nav:"))

    # ── Free text messages (state machine routes them) ────────────────────
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_checkin_message)
    )

    return app
