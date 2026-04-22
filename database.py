import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager
from typing import List, Optional

DB_PATH = "reddit_monitor.db"


def init_db():
    """Initialize database and create tables; run column migrations."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id       TEXT NOT NULL,
                    subreddit     TEXT NOT NULL,
                    title         TEXT,
                    selftext      TEXT,
                    score         INTEGER,
                    upvote_ratio  REAL,
                    num_comments  INTEGER,
                    author        TEXT,
                    created_utc   INTEGER,
                    fetch_date    TEXT,
                    category      TEXT,
                    top_comments  TEXT,
                    UNIQUE(post_id, fetch_date)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id       TEXT NOT NULL UNIQUE,
                    sentiment     TEXT,
                    content_type  TEXT,
                    user_type     TEXT,
                    key_topics    TEXT,
                    summary       TEXT,
                    analyzed_at   TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subreddits (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    name          TEXT NOT NULL UNIQUE,
                    added_at      TEXT
                )
            """)
            conn.commit()
            print("[DB] subreddits table created or already exists")

            # Migration: add top_comments to existing tables that don't have it
            try:
                cursor.execute("ALTER TABLE posts ADD COLUMN top_comments TEXT")
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Migration: add user_type_confidence to analysis table
            try:
                cursor.execute("ALTER TABLE analysis ADD COLUMN user_type_confidence TEXT DEFAULT 'medium'")
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Column already exists

    except Exception as e:
        print(f"[DB] Error initializing database: {e}")


@contextmanager
def get_connection():
    """Yield a SQLite connection and close it after use."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def insert_post(post_data: dict) -> bool:
    """Insert a post record; ignore if (post_id, fetch_date) already exists."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO posts
                    (post_id, subreddit, title, selftext, score, upvote_ratio,
                     num_comments, author, created_utc, fetch_date, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post_data["post_id"],
                    post_data["subreddit"],
                    post_data.get("title", ""),
                    post_data.get("selftext", ""),
                    post_data.get("score", 0),
                    post_data.get("upvote_ratio", 0.0),
                    post_data.get("num_comments", 0),
                    post_data.get("author", ""),
                    post_data.get("created_utc", 0),
                    post_data["fetch_date"],
                    post_data["category"],
                ),
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"[DB] Error inserting post {post_data.get('post_id')}: {e}")
        return False


def update_post_comments(post_id: str, fetch_date: str, comments: List[str]) -> None:
    """Store top comments JSON for a post (called after insert_post)."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE posts SET top_comments = ? WHERE post_id = ? AND fetch_date = ?",
                (json.dumps(comments, ensure_ascii=False), post_id, fetch_date),
            )
            conn.commit()
    except Exception as e:
        print(f"[DB] Error updating comments for {post_id}: {e}")


def insert_analysis(post_id: str, analysis_data: dict) -> bool:
    """Insert or replace the analysis result for a post."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO analysis
                    (post_id, sentiment, content_type, user_type, user_type_confidence,
                     key_topics, summary, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post_id,
                    analysis_data.get("sentiment", "neutral"),
                    analysis_data.get("content_type", "other"),
                    analysis_data.get("user_type", "unknown"),
                    analysis_data.get("user_type_confidence", "medium"),
                    json.dumps(analysis_data.get("key_topics", []), ensure_ascii=False),
                    analysis_data.get("summary", ""),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"[DB] Error inserting analysis for {post_id}: {e}")
        return False


def get_posts_needing_analysis() -> List[dict]:
    """Return posts that have no analysis record yet."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT p.* FROM posts p
                LEFT JOIN analysis a ON p.post_id = a.post_id
                WHERE a.post_id IS NULL
                """
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[DB] Error fetching posts needing analysis: {e}")
        return []


def get_posts_with_analysis(
    fetch_date: Optional[str] = None,
    subreddits: Optional[List[str]] = None,
) -> List[dict]:
    """Return posts joined with analysis, with optional filters, sorted by score desc."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT p.*, a.sentiment, a.content_type, a.user_type,
                       a.user_type_confidence, a.key_topics, a.summary
                FROM posts p
                LEFT JOIN analysis a ON p.post_id = a.post_id
                WHERE 1=1
            """
            params: list = []
            if fetch_date:
                query += " AND p.fetch_date = ?"
                params.append(fetch_date)
            if subreddits:
                placeholders = ",".join("?" * len(subreddits))
                query += f" AND p.subreddit IN ({placeholders})"
                params.extend(subreddits)
            query += " ORDER BY p.score DESC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"[DB] Error fetching posts with analysis: {e}")
        return []


def get_available_dates() -> List[str]:
    """Return all fetch_date values that exist in the posts table, newest first."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT fetch_date FROM posts ORDER BY fetch_date DESC"
            )
            return [row["fetch_date"] for row in cursor.fetchall()]
    except Exception as e:
        print(f"[DB] Error fetching available dates: {e}")
        return []


def get_all_subreddits(default: Optional[List[str]] = None) -> List[str]:
    """Get all subreddits from config file or database; return defaults if empty."""
    import os

    # First try to load from config file (JSON) - this persists on Streamlit Cloud
    config_file = "subreddit_config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                data = json.load(f)
                subs = data.get("subreddits", [])
                if subs:
                    print(f"[Config] Loaded {len(subs)} subreddits from config file")
                    return subs
        except Exception as e:
            print(f"[Config] Error reading config file: {e}")

    # Fallback to database
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM subreddits ORDER BY added_at DESC")
            subs = [row["name"] for row in cursor.fetchall()]
            if subs:
                return subs
    except Exception as e:
        print(f"[DB] Error fetching subreddits: {e}")

    return default or []


def add_subreddit(name: str) -> bool:
    """Add a new subreddit to both database and config file."""
    import os

    success = False

    # Save to database
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO subreddits (name, added_at) VALUES (?, ?)",
                (name, datetime.now().isoformat())
            )
            conn.commit()
            success = cursor.rowcount > 0
            print(f"[DB] Added subreddit to database: {name}")
    except Exception as e:
        print(f"[DB] Error adding subreddit to database: {e}")

    # Save to config file (for persistence on Streamlit Cloud)
    try:
        config_file = "subreddit_config.json"
        subs = []

        # Read existing
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                data = json.load(f)
                subs = data.get("subreddits", [])

        # Add new if not exists
        if name not in subs:
            subs.append(name)
            with open(config_file, "w") as f:
                json.dump({"subreddits": subs}, f, indent=2)
            print(f"[Config] Added subreddit to config file: {name}")
            success = True
        else:
            print(f"[Config] Subreddit already in config: {name}")

    except Exception as e:
        print(f"[Config] Error adding to config file: {e}")

    return success


def init_default_subreddits(defaults: List[str]) -> None:
    """Initialize database with default subreddits if table is empty."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # First ensure table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subreddits (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    name          TEXT NOT NULL UNIQUE,
                    added_at      TEXT
                )
            """)
            conn.commit()

            # Check and initialize defaults
            cursor.execute("SELECT COUNT(*) as cnt FROM subreddits")
            if cursor.fetchone()["cnt"] == 0:
                print("[DB] Initializing default subreddits...")
                for sub in defaults:
                    try:
                        cursor.execute(
                            "INSERT INTO subreddits (name, added_at) VALUES (?, ?)",
                            (sub, datetime.now().isoformat())
                        )
                        print(f"[DB]   ✓ Added: {sub}")
                    except sqlite3.IntegrityError:
                        pass  # Already exists
                conn.commit()
    except Exception as e:
        print(f"[DB] Error initializing default subreddits: {e}")
