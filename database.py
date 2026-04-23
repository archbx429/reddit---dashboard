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
    """Get all subreddits from config file (version-controlled source of truth)."""
    import os

    # Priority 1: Load from config file (version-controlled, auto-updated on GitHub)
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

    # Priority 2: Fallback to database (for backward compatibility)
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM subreddits ORDER BY added_at DESC")
            subs = [row["name"] for row in cursor.fetchall()]
            if subs:
                print(f"[DB] Loaded {len(subs)} subreddits from database (fallback)")
                return subs
    except Exception as e:
        print(f"[DB] Error fetching subreddits: {e}")

    return default or []


def add_subreddit(name: str) -> tuple:
    """Add a new subreddit to config file and attempt to auto-commit to GitHub.

    Returns: (success: bool, message: str)
    - success: Whether the subreddit was added locally
    - message: Detailed status message for user feedback
    """
    import os
    import subprocess
    import threading
    import sys
    import time as time_module

    success = False
    message = ""

    try:
        config_file = "subreddit_config.json"
        subs = []

        print(f"[Config] ========== 开始添加频道: {name} ==========", file=sys.stderr)
        print(f"[Config] 工作目录: {os.getcwd()}", file=sys.stderr)
        print(f"[Config] 配置文件路径: {os.path.abspath(config_file)}", file=sys.stderr)

        # Read existing
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                data = json.load(f)
                subs = data.get("subreddits", [])
            print(f"[Config] ✓ 读取成功，当前有 {len(subs)} 个频道: {subs}", file=sys.stderr)
        else:
            print(f"[Config] ⚠️ 配置文件不存在，将创建新文件", file=sys.stderr)

        # Add new if not exists (case-insensitive check)
        if name.lower() not in [s.lower() for s in subs]:
            print(f"[Config] → 频道不存在，准备添加...", file=sys.stderr)
            subs.append(name)
            print(f"[Config] → 内存中的列表已更新: {subs}", file=sys.stderr)

            # Write to file with multiple attempts
            max_write_attempts = 3
            write_success = False
            last_write_error = None

            for attempt in range(max_write_attempts):
                try:
                    with open(config_file, "w") as f:
                        json.dump({"subreddits": subs}, f, indent=2, ensure_ascii=False)
                    print(f"[Config] ✓ 写入完成（第 {attempt+1} 次尝试）", file=sys.stderr)
                    write_success = True
                    break
                except Exception as write_error:
                    last_write_error = write_error
                    print(f"[Config] ⚠️ 写入失败（第 {attempt+1} 次）: {write_error}", file=sys.stderr)
                    time_module.sleep(0.1)

            if not write_success:
                print(f"[Config] ❌ 多次写入尝试都失败了", file=sys.stderr)
                raise Exception(f"文件写入失败: {last_write_error}")

            # Verify write was successful
            print(f"[Config] → 验证写入...", file=sys.stderr)
            time_module.sleep(0.1)  # 等待文件系统同步

            try:
                with open(config_file, "r") as f:
                    verify_data = json.load(f)
                    verify_subs = verify_data.get("subreddits", [])
                print(f"[Config] ✓ 验证读取成功: {verify_subs}", file=sys.stderr)
            except Exception as verify_error:
                print(f"[Config] ❌ 验证读取失败: {verify_error}", file=sys.stderr)
                raise

            # Check if new subreddit is in the verified list (case-sensitive exact match)
            print(f"[Config] 检查 {name} 是否在 {verify_subs} 中...", file=sys.stderr)
            if name in verify_subs:
                print(f"[Config] ✅ 验证通过: {name} 确实在文件中", file=sys.stderr)
                success = True
                message = f"✅ {name} 已添加到配置文件"

                # Auto-commit to GitHub in background (doesn't block)
                def git_commit_async():
                    try:
                        subprocess.run(["git", "add", config_file], capture_output=True, text=True, timeout=5)
                        subprocess.run(
                            ["git", "commit", "-m", f"Add {name} subreddit to config\n\nCo-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"],
                            capture_output=True, text=True, timeout=10
                        )
                        subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, timeout=10)
                        print(f"[Git] ✅ 成功提交 {name} 到 GitHub", file=sys.stderr)
                    except Exception as git_error:
                        print(f"[Git] ⚠️ Git 提交失败（但本地配置已保存）: {git_error}", file=sys.stderr)

                git_thread = threading.Thread(target=git_commit_async, daemon=True)
                git_thread.start()
            else:
                print(f"[Config] ❌ 验证失败: {name} 不在验证读取的列表中", file=sys.stderr)
                print(f"[Config] 预期找到: {name}", file=sys.stderr)
                print(f"[Config] 实际列表: {verify_subs}", file=sys.stderr)
                print(f"[Config] 列表长度: {len(verify_subs)}", file=sys.stderr)
                success = False
                message = f"❌ 添加失败：文件写入验证失败（文件可能无法写入）"
        else:
            print(f"[Config] ⚠️ {name} 已存在于配置文件中", file=sys.stderr)
            message = f"⚠️ {name} 已经存在"

    except Exception as e:
        print(f"[Config] ❌ 异常: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        print(f"[Config] 堆栈跟踪: {traceback.format_exc()}", file=sys.stderr)
        message = f"❌ 错误: {str(e)}"

    print(f"[Config] 最终结果: success={success}, message={message}", file=sys.stderr)
    print(f"[Config] ========== 添加流程结束 ==========", file=sys.stderr)
    return success, message


def delete_subreddit(name: str) -> tuple:
    """Delete a subreddit from config file.

    Returns: (success: bool, message: str)
    """
    import os
    import subprocess
    import threading
    import sys

    success = False
    message = ""

    try:
        config_file = "subreddit_config.json"

        print(f"[Config] ========== 开始删除频道: {name} ==========", file=sys.stderr)

        # Read existing
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                data = json.load(f)
                subs = data.get("subreddits", [])
            print(f"[Config] ✓ 读取成功，当前有 {len(subs)} 个频道", file=sys.stderr)
        else:
            print(f"[Config] ❌ 配置文件不存在", file=sys.stderr)
            message = "❌ 错误: 配置文件不存在"
            return False, message

        # Remove if exists (case-insensitive check)
        if name.lower() in [s.lower() for s in subs]:
            print(f"[Config] → 频道存在，准备删除...", file=sys.stderr)
            subs = [s for s in subs if s.lower() != name.lower()]
            print(f"[Config] → 内存中的列表已更新: {subs}", file=sys.stderr)

            # Write to file
            try:
                with open(config_file, "w") as f:
                    json.dump({"subreddits": subs}, f, indent=2)
                print(f"[Config] ✓ 写入完成", file=sys.stderr)
            except Exception as write_error:
                print(f"[Config] ❌ 写入失败: {write_error}", file=sys.stderr)
                raise

            # Verify deletion
            print(f"[Config] → 验证删除...", file=sys.stderr)
            try:
                with open(config_file, "r") as f:
                    verify_data = json.load(f)
                    verify_subs = verify_data.get("subreddits", [])
                print(f"[Config] ✓ 验证读取成功: {verify_subs}", file=sys.stderr)
            except Exception as verify_error:
                print(f"[Config] ❌ 验证读取失败: {verify_error}", file=sys.stderr)
                raise

            # Check if subreddit is really deleted
            if name.lower() not in [s.lower() for s in verify_subs]:
                print(f"[Config] ✅ 验证通过: {name} 已被删除", file=sys.stderr)
                success = True
                message = f"✅ {name} 已从配置文件删除"

                # Auto-commit to GitHub in background
                def git_commit_async():
                    try:
                        subprocess.run(["git", "add", config_file], capture_output=True, text=True, timeout=5)
                        subprocess.run(
                            ["git", "commit", "-m", f"Remove {name} subreddit from config\n\nCo-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"],
                            capture_output=True, text=True, timeout=10
                        )
                        subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True, timeout=10)
                        print(f"[Git] ✅ 成功提交删除 {name} 到 GitHub", file=sys.stderr)
                    except Exception as git_error:
                        print(f"[Git] ⚠️ Git 提交失败（但本地配置已保存）: {git_error}", file=sys.stderr)

                git_thread = threading.Thread(target=git_commit_async, daemon=True)
                git_thread.start()
            else:
                print(f"[Config] ❌ 验证失败: {name} 仍在列表中", file=sys.stderr)
                success = False
                message = f"❌ 删除失败：验证出错"
        else:
            print(f"[Config] ⚠️ {name} 不在配置文件中", file=sys.stderr)
            message = f"⚠️ {name} 不在频道列表中"

    except Exception as e:
        print(f"[Config] ❌ 异常: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        print(f"[Config] 堆栈跟踪: {traceback.format_exc()}", file=sys.stderr)
        message = f"❌ 错误: {str(e)}"

    print(f"[Config] 最终结果: success={success}, message={message}", file=sys.stderr)
    print(f"[Config] ========== 删除流程结束 ==========", file=sys.stderr)
    return success, message


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
