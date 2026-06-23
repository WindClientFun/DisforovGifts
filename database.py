import sqlite3
import threading
from datetime import date

DB_PATH = "bot_database.db"
_local = threading.local()


def get_conn():
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS gifts (
            gift_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            emoji TEXT NOT NULL,
            star_cost INTEGER NOT NULL DEFAULT 15
        );

        CREATE TABLE IF NOT EXISTS daily_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            message_count INTEGER DEFAULT 1,
            UNIQUE(user_id, chat_id, date)
        );

        CREATE TABLE IF NOT EXISTS giveaway_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            gift_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            given_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            total_messages INTEGER DEFAULT 0,
            giveaway_done INTEGER DEFAULT 0,
            x2_active INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    _seed_gifts(conn)

    try:
        conn.execute("ALTER TABLE daily_stats ADD COLUMN x2_active INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass


def _seed_gifts(conn):
    if conn.execute("SELECT COUNT(*) FROM gifts").fetchone()[0] > 0:
        return
    gifts = [
        ("Мишка", "🧸", 15),
        ("Сердечко", "❤️", 15),
        ("Роза", "🌹", 25),
        ("Подарок", "🎁", 25),
        ("Ракета", "🚀", 50),
        ("Торт", "🎂", 50),
        ("Букет", "💐", 50),
        ("Кольцо", "💍", 100),
        ("Кубок", "🏆", 100),
        ("Алмаз", "💎", 100),
    ]
    for name, emoji, cost in gifts:
        conn.execute("INSERT INTO gifts (name, emoji, star_cost) VALUES (?, ?, ?)", (name, emoji, cost))
    conn.commit()


def get_or_create_user(user_id: int, username: str = "", first_name: str = ""):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (user_id, username, first_name))
    conn.execute("UPDATE users SET username = ?, first_name = ? WHERE user_id = ?", (username, first_name, user_id))
    conn.commit()


def track_message(user_id: int, chat_id: int, username: str = "", first_name: str = ""):
    get_or_create_user(user_id, username, first_name)
    conn = get_conn()
    today = date.today().isoformat()
    conn.execute("""
        INSERT INTO daily_activity (user_id, chat_id, date, message_count)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(user_id, chat_id, date)
        DO UPDATE SET message_count = message_count + 1
    """, (user_id, chat_id, today))
    conn.execute("""
        INSERT INTO daily_stats (chat_id, date, total_messages)
        VALUES (?, ?, 1)
        ON CONFLICT(id) DO NOTHING
    """, (chat_id, today))
    conn.execute("""
        UPDATE daily_stats SET total_messages = total_messages + 1
        WHERE chat_id = ? AND date = ?
    """, (chat_id, today))
    conn.commit()


def get_top_users(chat_id: int, limit: int = 25):
    conn = get_conn()
    today = date.today().isoformat()
    rows = conn.execute("""
        SELECT da.user_id, da.message_count, u.username, u.first_name
        FROM daily_activity da
        JOIN users u ON da.user_id = u.user_id
        WHERE da.chat_id = ? AND da.date = ?
        ORDER BY da.message_count DESC
        LIMIT ?
    """, (chat_id, today, limit)).fetchall()
    return [dict(r) for r in rows]


def get_total_messages(chat_id: int):
    conn = get_conn()
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT total_messages FROM daily_stats WHERE chat_id = ? AND date = ?",
        (chat_id, today),
    ).fetchone()
    return row[0] if row else 0


def set_giveaway_done(chat_id: int):
    conn = get_conn()
    today = date.today().isoformat()
    conn.execute(
        "UPDATE daily_stats SET giveaway_done = 1 WHERE chat_id = ? AND date = ?",
        (chat_id, today),
    )
    conn.commit()


def is_giveaway_done(chat_id: int) -> bool:
    conn = get_conn()
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT giveaway_done FROM daily_stats WHERE chat_id = ? AND date = ?",
        (chat_id, today),
    ).fetchone()
    return row[0] == 1 if row else False


def get_random_gift(min_stars: int = 0, max_stars: int = 0):
    conn = get_conn()
    if min_stars > 0:
        rows = conn.execute("SELECT * FROM gifts WHERE star_cost >= ? ORDER BY RANDOM() LIMIT 1", (min_stars,)).fetchall()
    elif max_stars > 0:
        rows = conn.execute("SELECT * FROM gifts WHERE star_cost <= ? ORDER BY RANDOM() LIMIT 1", (max_stars,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM gifts ORDER BY RANDOM() LIMIT 1").fetchall()
    return dict(rows[0]) if rows else None


def get_random_gift_by_name(name: str):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM gifts WHERE name = ? ORDER BY RANDOM() LIMIT 1", (name,)).fetchall()
    return dict(rows[0]) if rows else None


def set_x2(chat_id: int, active: bool):
    conn = get_conn()
    today = date.today().isoformat()
    conn.execute("""
        INSERT INTO daily_stats (chat_id, date, x2_active)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET x2_active = ?
    """, (chat_id, today, int(active), int(active)))
    conn.commit()


def get_x2(chat_id: int) -> bool:
    conn = get_conn()
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT x2_active FROM daily_stats WHERE chat_id = ? AND date = ?",
        (chat_id, today),
    ).fetchone()
    return row[0] == 1 if row else False


def log_giveaway(user_id: int, gift_id: int, chat_id: int):
    conn = get_conn()
    conn.execute("INSERT INTO giveaway_log (user_id, gift_id, chat_id) VALUES (?, ?, ?)", (user_id, gift_id, chat_id))
    conn.commit()
