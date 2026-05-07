import logging
import sys
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    filters,
)

import database as db
from handlers import (
    handle_message,
    handle_forum_topic_created,
    cmd_report,
    cmd_user,
    cmd_rule,
)
from scheduler import create_scheduler
from config import TELEGRAM_BOT_TOKEN

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.INFO)

logger = logging.getLogger(__name__)


async def post_init(application: Application):
    db.init_db()
    scheduler = create_scheduler(application.bot)
    scheduler.start()
    application.bot_data["scheduler"] = scheduler
    logger.info("Bot started. Scheduler running.")


async def post_shutdown(application: Application):
    scheduler = application.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("Bot shut down cleanly.")


def main():
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.add_handler(
        MessageHandler(
            filters.StatusUpdate.FORUM_TOPIC_CREATED,
            handle_forum_topic_created,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.ChatType.SUPERGROUP & ~filters.COMMAND,
            handle_message,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.ChatType.GROUP & ~filters.COMMAND,
            handle_message,
        )
    )

    application.add_handler(CommandHandler("report", cmd_report))
    application.add_handler(CommandHandler("user", cmd_user))
    application.add_handler(CommandHandler("rule", cmd_rule))

    logger.info("Starting polling…")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
