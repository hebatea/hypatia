"""
Hypatia — entrypoint.

Starts:
  1. Database (create tables if needed)
  2. Telegram bot (polling)
  3. APScheduler (reminder job) — runs inside the same async loop

Run: python main.py
"""
import asyncio
import logging

from app.bot import create_bot
from app.db.engine import init_db
from app.services.scheduler import create_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    # 1. Database
    logger.info("Initialising database…")
    await init_db()
    logger.info("Database ready ✓")

    # 2. Bot
    app = create_bot()
    await app.initialize()

    # 3. Scheduler — pass the bot instance so it can send messages
    scheduler = create_scheduler(app.bot)
    scheduler.start()
    logger.info("Scheduler started ✓")

    # 4. Start polling
    logger.info("Bot starting… Press Ctrl+C to stop.")
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    # Keep running until interrupted
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        logger.info("Shutting down…")
        scheduler.shutdown(wait=False)
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        logger.info("Goodbye.")


if __name__ == "__main__":
    asyncio.run(main())
