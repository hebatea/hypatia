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
    handle_voice_message,
)
from app.handlers.onboarding import (
    callback_reminder_time,
    callback_timezone,
    cmd_start,
)
from app.handlers.settings import (
    callback_delete,
    callback_nav,
    cmd_deletedata,
    cmd_history,
    cmd_myhistory,
    cmd_pause,
    cmd_remind,
    cmd_resume,
    cmd_streak,
)
from app.handlers.steps import (
    callback_step,
    cmd_step1,
    handle_step_message,
    handle_step_voice,
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
    app.add_handler(CommandHandler("myhistory", cmd_myhistory))
    app.add_handler(CommandHandler("remind", cmd_remind))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))
    app.add_handler(CommandHandler("step1", cmd_step1))
    app.add_handler(CommandHandler("deletedata", cmd_deletedata))

    # ── Callback queries ──────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(callback_timezone, pattern=r"^tz:"))
    app.add_handler(CallbackQueryHandler(callback_reminder_time, pattern=r"^rt:"))
    app.add_handler(CallbackQueryHandler(callback_checkin_flow, pattern=r"^checkin:"))
    app.add_handler(CallbackQueryHandler(callback_nav, pattern=r"^nav:"))
    app.add_handler(CallbackQueryHandler(callback_step, pattern=r"^step:"))
    app.add_handler(CallbackQueryHandler(callback_delete, pattern=r"^delete:"))

    # ── Free text messages ────────────────────────────────────────────────
    # Group 0: check-in flow. Group 1: step flows.
    # PTB runs each group independently, so both handlers always get a chance.
    # Each handler returns early if the user's state doesn't match its flow.
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_checkin_message),
        group=0,
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_step_message),
        group=1,
    )

    # ── Voice messages ────────────────────────────────────────────────────
    app.add_handler(
        MessageHandler(filters.VOICE, handle_voice_message),
        group=0,
    )
    app.add_handler(
        MessageHandler(filters.VOICE, handle_step_voice),
        group=1,
    )

    return app

