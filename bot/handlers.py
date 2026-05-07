import logging
from datetime import date
from telegram import Update, Message
from telegram.ext import ContextTypes
from telegram.constants import ChatType

import database as db
from config import (
    TOPIC_CATEGORIES, IGNORE_KEYWORDS, TOTAL_CATEGORIES,
    ALERT_EMOJIS, ALERT_MESSAGES
)

logger = logging.getLogger(__name__)


def classify_topic(topic_name: str) -> tuple[str | None, bool]:
    """Return (category_key, is_announcement). category_key is None if ignored or unknown."""
    lower = topic_name.lower()
    for kw in IGNORE_KEYWORDS:
        if kw in lower:
            return None, True
    for cat_key, kw in TOPIC_CATEGORIES.items():
        if kw in lower:
            return cat_key, False
    return None, False


def is_forum_group(message: Message) -> bool:
    return message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP) and message.is_topic_message


def get_display_name(user) -> str:
    if user.username:
        return f"@{user.username}"
    full = user.full_name.strip()
    return full or f"user_{user.id}"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not user or not chat:
        return
    if user.is_bot:
        return
    if not is_forum_group(message):
        return

    group_id = chat.id
    topic_id = message.message_thread_id
    username = user.username

    db.upsert_member(
        group_id, user.id, username,
        user.first_name, user.last_name
    )

    if topic_id is None:
        return

    topic_row = db.get_topic(group_id, topic_id)

    if topic_row is None:
        topic_name = _extract_topic_name(message)
        if topic_name:
            category, is_announcement = classify_topic(topic_name)
            db.upsert_topic(group_id, topic_id, topic_name, category, is_announcement)
            if is_announcement:
                db.upsert_announcement_topic(group_id, topic_id, topic_name)
            topic_row = db.get_topic(group_id, topic_id)

    if not topic_row:
        return

    if topic_row["is_announcement"]:
        return

    category = topic_row["category"]
    if not category:
        return

    db.record_activity(group_id, user.id, username, category)
    logger.debug("Recorded %s → %s for user %s in group %s", category, date.today(), user.id, group_id)


def _extract_topic_name(message: Message) -> str | None:
    if message.reply_to_message and message.reply_to_message.forum_topic_created:
        return message.reply_to_message.forum_topic_created.name
    if hasattr(message, "forum_topic_created") and message.forum_topic_created:
        return message.forum_topic_created.name
    return None


async def handle_forum_topic_created(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    if not message or not chat:
        return
    if not message.forum_topic_created:
        return

    group_id = chat.id
    topic_id = message.message_thread_id
    topic_name = message.forum_topic_created.name

    category, is_announcement = classify_topic(topic_name)
    db.upsert_topic(group_id, topic_id, topic_name, category, is_announcement)

    if is_announcement:
        db.upsert_announcement_topic(group_id, topic_id, topic_name)
        logger.info("Registered announcement topic '%s' in group %s", topic_name, group_id)
    elif category:
        logger.info("Registered topic '%s' → category %s in group %s", topic_name, category, group_id)
    else:
        logger.info("Topic '%s' in group %s has no matching category", topic_name, group_id)


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not chat or not user:
        return

    member = await chat.get_member(user.id)
    if member.status not in ("administrator", "creator"):
        await message.reply_text("⚠️ Only admins can use /report.")
        return

    group_id = chat.id
    rows = db.get_group_activity_range(group_id, days=7)

    if not rows:
        await message.reply_text("No activity data found for the last 7 days.")
        return

    from collections import defaultdict
    by_user: dict[int, dict] = defaultdict(lambda: {"username": None, "days": {}})
    for row in rows:
        uid = row["user_id"]
        by_user[uid]["username"] = row["username"]
        by_user[uid]["days"][row["activity_date"]] = row["categories_done"]

    lines = ["📊 *7-Day Activity Report*\n"]
    for uid, data in by_user.items():
        uname = f"@{data['username']}" if data["username"] else f"User {uid}"
        total_days_active = len(data["days"])
        avg = sum(data["days"].values()) / max(len(data["days"]), 1)
        lines.append(f"👤 {uname}")
        lines.append(f"   Active days: {total_days_active}/7  |  Avg categories/day: {avg:.1f}")
        for d, cnt in sorted(data["days"].items(), reverse=True):
            lines.append(f"   {d}: {cnt}/{TOTAL_CATEGORIES} ✅")
        lines.append("")

    await message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not chat or not user:
        return

    member = await chat.get_member(user.id)
    if member.status not in ("administrator", "creator"):
        await message.reply_text("⚠️ Only admins can use /user.")
        return

    if not context.args:
        await message.reply_text("Usage: /user @username")
        return

    target_username = context.args[0]
    group_id = chat.id
    target = db.find_member_by_username(group_id, target_username)

    if not target:
        await message.reply_text(f"User {target_username} not found in this group's records.")
        return

    rows = db.get_user_activity_range(group_id, target["user_id"], days=7)
    uname = f"@{target['username']}" if target["username"] else target["first_name"]

    lines = [f"👤 *User Details: {uname}*\n"]
    if not rows:
        lines.append("No activity in the last 7 days.")
    else:
        for row in rows:
            cats = row["categories"]
            cnt = row["count"]
            lines.append(f"📅 {row['activity_date']}: {cnt}/{TOTAL_CATEGORIES} categories")
            lines.append(f"   ✅ {cats}")

    today_cats = db.get_user_activity_today(group_id, target["user_id"])
    lines.append(f"\n📍 *Today so far:* {len(today_cats)}/{TOTAL_CATEGORIES}")
    if today_cats:
        lines.append("   " + ", ".join(today_cats))
    else:
        lines.append("   No activity yet today.")

    await message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_rule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message:
        return

    from config import TOPIC_CATEGORIES, IGNORE_KEYWORDS
    cat_lines = "\n".join(
        f"  • *{k}* — topic name contains `{v}`"
        for k, v in TOPIC_CATEGORIES.items()
    )
    ignore_lines = ", ".join(f"`{w}`" for w in IGNORE_KEYWORDS)

    text = f"""
📋 *JEE Mentorship Bot — Rules & Logic*

━━━━━━━━━━━━━━━━━━━━
*Tracked Topic Categories ({TOTAL_CATEGORIES} total)*
{cat_lines}

*Ignored Topics*
Any topic whose name contains: {ignore_lines}

━━━━━━━━━━━━━━━━━━━━
*Activity Tracking*
• One message in a required topic = that category is ✅ for the day.
• Activity is tracked per user, per group, per day.
• Announcement topics are completely ignored.

━━━━━━━━━━━━━━━━━━━━
*Daily 3 AM Auto-Alert (last 24 hours)*
Every day at 3:00 AM IST the bot checks all members:

🔴 *HIGH ALERT* — 0/{TOTAL_CATEGORIES} categories done
🟠 *MID ALERT* — 1–3/{TOTAL_CATEGORIES} categories done
🟡 *LOW ALERT* — 4–6/{TOTAL_CATEGORIES} categories done
✅ *No alert* — {TOTAL_CATEGORIES}/{TOTAL_CATEGORIES} done (all complete)

Alerts are posted inside the Announcement topic of each group.

━━━━━━━━━━━━━━━━━━━━
*Admin Commands*
/report — 7-day activity report (run in any topic)
/user @username — detailed stats for one student
/rule — this message
""".strip()

    await message.reply_text(text, parse_mode="Markdown")


def build_daily_alert_text(rows: list) -> str:
    """Build the 3 AM alert message from query rows."""
    high, mid, low = [], [], []

    for row in rows:
        done = row["categories_done"]
        uname = f"@{row['username']}" if row["username"] else row["first_name"] or f"User {row['user_id']}"

        if done == TOTAL_CATEGORIES:
            continue
        elif done == 0:
            high.append(uname)
        elif 1 <= done <= 3:
            mid.append(uname)
        else:
            low.append(uname)

    parts = []

    if high:
        lines = [f"🔴 *HIGH ALERT*"]
        for u in high:
            lines.append(f"{u} {ALERT_MESSAGES['HIGH']}")
        parts.append("\n".join(lines))

    if mid:
        lines = [f"🟠 *MID ALERT*"]
        for u in mid:
            lines.append(f"{u} {ALERT_MESSAGES['MID']}")
        parts.append("\n".join(lines))

    if low:
        lines = [f"🟡 *LOW ALERT*"]
        for u in low:
            lines.append(f"{u} {ALERT_MESSAGES['LOW']}")
        parts.append("\n".join(lines))

    if not parts:
        return "✅ All students completed all topics today! Great work!"

    header = f"📢 *Daily Activity Alert — {date.today()}*\n"
    return header + "\n\n".join(parts)
