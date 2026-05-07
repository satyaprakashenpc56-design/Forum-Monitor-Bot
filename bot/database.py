import sqlite3
import logging
from datetime import date, timedelta
from contextlib import contextmanager
from config import DB_PATH

logger = logging.getLogger(__name__)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                category TEXT NOT NULL,
                activity_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_id, user_id, category, activity_date)
            );

            CREATE TABLE IF NOT EXISTS forum_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                topic_id INTEGER NOT NULL,
                topic_name TEXT NOT NULL,
                category TEXT,
                is_announcement INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_id, topic_id)
            );

            CREATE TABLE IF NOT EXISTS announcement_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                topic_id INTEGER NOT NULL,
                topic_name TEXT,
                UNIQUE(group_id, topic_id)
            );

            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_id, user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_activity_date ON activity(activity_date);
            CREATE INDEX IF NOT EXISTS idx_activity_group ON activity(group_id);
            CREATE INDEX IF NOT EXISTS idx_activity_user ON activity(user_id);
        """)
    logger.info("Database initialised at %s", DB_PATH)


def upsert_topic(group_id: int, topic_id: int, topic_name: str, category: str | None, is_announcement: bool):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO forum_topics (group_id, topic_id, topic_name, category, is_announcement, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(group_id, topic_id) DO UPDATE SET
                topic_name=excluded.topic_name,
                category=excluded.category,
                is_announcement=excluded.is_announcement,
                updated_at=CURRENT_TIMESTAMP
        """, (group_id, topic_id, topic_name, category, int(is_announcement)))


def get_topic(group_id: int, topic_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM forum_topics WHERE group_id=? AND topic_id=?",
            (group_id, topic_id)
        ).fetchone()


def upsert_announcement_topic(group_id: int, topic_id: int, topic_name: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO announcement_topics (group_id, topic_id, topic_name)
            VALUES (?, ?, ?)
        """, (group_id, topic_id, topic_name))


def get_announcement_topics(group_id: int) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM announcement_topics WHERE group_id=?", (group_id,)
        ).fetchall()


def upsert_member(group_id: int, user_id: int, username: str | None, first_name: str, last_name: str | None):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO group_members (group_id, user_id, username, first_name, last_name, last_seen)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(group_id, user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                last_seen=CURRENT_TIMESTAMP
        """, (group_id, user_id, username, first_name, last_name))


def record_activity(group_id: int, user_id: int, username: str | None, category: str, day: date | None = None):
    day = day or date.today()
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO activity (group_id, user_id, username, category, activity_date)
            VALUES (?, ?, ?, ?, ?)
        """, (group_id, user_id, username, category, day.isoformat()))


def get_active_groups() -> list[int]:
    with get_conn() as conn:
        rows = conn.execute("SELECT DISTINCT group_id FROM group_members").fetchall()
        return [r["group_id"] for r in rows]


def get_group_members(group_id: int) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM group_members WHERE group_id=?", (group_id,)
        ).fetchall()


def get_user_activity_today(group_id: int, user_id: int, day: date | None = None) -> list[str]:
    day = day or date.today()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT category FROM activity
            WHERE group_id=? AND user_id=? AND activity_date=?
        """, (group_id, user_id, day.isoformat())).fetchall()
        return [r["category"] for r in rows]


def get_group_activity_range(group_id: int, days: int = 7) -> list[sqlite3.Row]:
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    with get_conn() as conn:
        return conn.execute("""
            SELECT user_id, username, activity_date, COUNT(DISTINCT category) as categories_done
            FROM activity
            WHERE group_id=? AND activity_date >= ?
            GROUP BY user_id, activity_date
            ORDER BY activity_date DESC, categories_done DESC
        """, (group_id, start)).fetchall()


def get_user_activity_range(group_id: int, user_id: int, days: int = 7) -> list[sqlite3.Row]:
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    with get_conn() as conn:
        return conn.execute("""
            SELECT activity_date, GROUP_CONCAT(category, ', ') as categories, COUNT(DISTINCT category) as count
            FROM activity
            WHERE group_id=? AND user_id=? AND activity_date >= ?
            GROUP BY activity_date
            ORDER BY activity_date DESC
        """, (group_id, user_id, start)).fetchall()


def find_member_by_username(group_id: int, username: str) -> sqlite3.Row | None:
    clean = username.lstrip("@").lower()
    with get_conn() as conn:
        return conn.execute("""
            SELECT * FROM group_members
            WHERE group_id=? AND LOWER(username)=?
        """, (group_id, clean)).fetchone()


def get_last_24h_all_users(group_id: int) -> list[sqlite3.Row]:
    today = date.today().isoformat()
    with get_conn() as conn:
        return conn.execute("""
            SELECT
                m.user_id, m.username, m.first_name,
                COUNT(DISTINCT a.category) as categories_done
            FROM group_members m
            LEFT JOIN activity a
                ON a.group_id=m.group_id AND a.user_id=m.user_id AND a.activity_date=?
            WHERE m.group_id=?
            GROUP BY m.user_id
        """, (today, group_id)).fetchall()
