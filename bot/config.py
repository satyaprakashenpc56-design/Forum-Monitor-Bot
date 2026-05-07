import os

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

TOPIC_CATEGORIES = {
    "TARGET": "target",
    "SCREEN_TIME": "screen",
    "STUDY_HOURS": "study",
    "TOTAL_TIME_WASTE": "waste",
    "REVISION": "revision",
    "QUESTIONS_SOLVED": "question",
    "TARGET_COMPLETION": "completion",
}

IGNORE_KEYWORDS = ["announcement", "announce"]

TOTAL_CATEGORIES = len(TOPIC_CATEGORIES)

ALERT_LEVELS = {
    "HIGH": (0, 0),
    "MID": (1, 3),
    "LOW": (4, 6),
    "NONE": (7, 7),
}

ALERT_EMOJIS = {
    "HIGH": "🔴",
    "MID": "🟠",
    "LOW": "🟡",
}

ALERT_MESSAGES = {
    "HIGH": "has not updated any required topic today.",
    "MID": "has low activity today.",
    "LOW": "missed some updates today.",
}

DB_PATH = os.environ.get("DB_PATH", "jee_bot.db")

ALERT_HOUR = 3
ALERT_MINUTE = 0
TIMEZONE = "Asia/Kolkata"
