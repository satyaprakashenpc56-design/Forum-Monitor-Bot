import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.error import TelegramError

import database as db
from handlers import build_daily_alert_text
from config import ALERT_HOUR, ALERT_MINUTE, TIMEZONE

logger = logging.getLogger(__name__)


async def send_daily_alerts(bot: Bot):
    logger.info("Running daily 3 AM alert job")
    groups = db.get_active_groups()

    if not groups:
        logger.info("No active groups found, skipping alert")
        return

    for group_id in groups:
        try:
            rows = db.get_last_24h_all_users(group_id)
            if not rows:
                logger.info("No members in group %s, skipping", group_id)
                continue

            alert_text = build_daily_alert_text(rows)
            ann_topics = db.get_announcement_topics(group_id)

            if not ann_topics:
                logger.warning(
                    "Group %s has no announcement topic registered — "
                    "send a message in the announcement topic so the bot can detect it",
                    group_id
                )
                continue

            for topic in ann_topics:
                try:
                    await bot.send_message(
                        chat_id=group_id,
                        message_thread_id=topic["topic_id"],
                        text=alert_text,
                        parse_mode="Markdown",
                    )
                    logger.info("Sent daily alert to group %s topic %s", group_id, topic["topic_id"])
                except TelegramError as e:
                    logger.error("Failed to send alert to group %s topic %s: %s", group_id, topic["topic_id"], e)

        except Exception:
            logger.exception("Unexpected error processing group %s", group_id)


def create_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        send_daily_alerts,
        trigger=CronTrigger(
            hour=ALERT_HOUR,
            minute=ALERT_MINUTE,
            timezone=TIMEZONE,
        ),
        args=[bot],
        id="daily_alert",
        name="Daily 3 AM Activity Alert",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info(
        "Scheduler configured: daily alert at %02d:%02d %s",
        ALERT_HOUR, ALERT_MINUTE, TIMEZONE
    )
    return scheduler
