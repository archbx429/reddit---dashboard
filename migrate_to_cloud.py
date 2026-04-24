"""
Migrate local SQLite database to SQLite Cloud.
Run this AFTER you've set up SQLite Cloud and configured SQLITE_CLOUD_URL.

Usage:
    python3 migrate_to_cloud.py
"""

import os
import sqlite3
import sys

# Check if cloud URL is set
CLOUD_URL = os.getenv("SQLITE_CLOUD_URL")
if not CLOUD_URL:
    print("❌ SQLITE_CLOUD_URL not set!")
    print("Please set the environment variable first:")
    print('   export SQLITE_CLOUD_URL="sqlitecloud://user:password@host/database"')
    sys.exit(1)

try:
    import sqlitecloud
except ImportError:
    print("❌ sqlitecloud not installed. Installing...")
    os.system("pip install sqlitecloud")
    import sqlitecloud

print("=" * 60)
print("📊 MIGRATE TO SQLITE CLOUD")
print("=" * 60)

# Connect to local database
print("\n[1] 连接本地数据库...")
local_conn = sqlite3.connect("reddit_monitor.db")
local_conn.row_factory = sqlite3.Row
print("✅ 连接成功")

# Connect to cloud database
print("\n[2] 连接 SQLite Cloud...")
try:
    cloud_conn = sqlitecloud.connect(CLOUD_URL)
    print("✅ 连接成功")
except Exception as e:
    print(f"❌ 连接失败: {e}")
    print("请检查 SQLITE_CLOUD_URL 是否正确")
    sys.exit(1)

cloud_cursor = cloud_conn.cursor()

# Create tables in cloud database
print("\n[3] 在云数据库创建表...")
tables_sql = [
    """
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
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id       TEXT NOT NULL UNIQUE,
        sentiment     TEXT,
        content_type  TEXT,
        user_type     TEXT,
        user_type_confidence TEXT DEFAULT 'medium',
        key_topics    TEXT,
        summary       TEXT,
        analyzed_at   TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS subreddits (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        name          TEXT NOT NULL UNIQUE,
        added_at      TEXT
    )
    """,
]

for sql in tables_sql:
    try:
        cloud_cursor.execute(sql)
        cloud_conn.commit()
    except Exception as e:
        if "already exists" in str(e):
            pass  # Table already exists
        else:
            print(f"⚠️  {e}")

print("✅ 表创建完成")

# Migrate posts
print("\n[4] 迁移 posts 表...")
local_cursor = local_conn.cursor()
local_cursor.execute("SELECT COUNT(*) FROM posts")
post_count = local_cursor.fetchone()[0]

if post_count > 0:
    local_cursor.execute("SELECT * FROM posts")
    posts = local_cursor.fetchall()

    for post in posts:
        try:
            cloud_cursor.execute("""
                INSERT OR IGNORE INTO posts
                (post_id, subreddit, title, selftext, score, upvote_ratio,
                 num_comments, author, created_utc, fetch_date, category, top_comments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(post))
        except Exception as e:
            print(f"⚠️  Failed to insert post: {e}")

    cloud_conn.commit()
    print(f"✅ 迁移了 {post_count} 条帖子")
else:
    print("ℹ️  没有帖子需要迁移")

# Migrate analysis
print("\n[5] 迁移 analysis 表...")
local_cursor.execute("SELECT COUNT(*) FROM analysis")
analysis_count = local_cursor.fetchone()[0]

if analysis_count > 0:
    local_cursor.execute("SELECT * FROM analysis")
    analyses = local_cursor.fetchall()

    for analysis in analyses:
        try:
            cloud_cursor.execute("""
                INSERT OR IGNORE INTO analysis
                (post_id, sentiment, content_type, user_type, user_type_confidence,
                 key_topics, summary, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(analysis))
        except Exception as e:
            print(f"⚠️  Failed to insert analysis: {e}")

    cloud_conn.commit()
    print(f"✅ 迁移了 {analysis_count} 条分析")
else:
    print("ℹ️  没有分析数据需要迁移")

# Migrate subreddits
print("\n[6] 迁移 subreddits 表...")
local_cursor.execute("SELECT COUNT(*) FROM subreddits")
subreddit_count = local_cursor.fetchone()[0]

if subreddit_count > 0:
    local_cursor.execute("SELECT * FROM subreddits")
    subreddits = local_cursor.fetchall()

    for subreddit in subreddits:
        try:
            cloud_cursor.execute("""
                INSERT OR IGNORE INTO subreddits (name, added_at)
                VALUES (?, ?)
            """, tuple(subreddit[1:]))  # Skip id
        except Exception as e:
            print(f"⚠️  Failed to insert subreddit: {e}")

    cloud_conn.commit()
    print(f"✅ 迁移了 {subreddit_count} 个频道")
else:
    print("ℹ️  没有频道数据需要迁移")

# Verify migration
print("\n[7] 验证迁移...")
cloud_cursor.execute("SELECT COUNT(*) FROM posts")
cloud_post_count = cloud_cursor.fetchone()[0]
cloud_cursor.execute("SELECT COUNT(*) FROM analysis")
cloud_analysis_count = cloud_cursor.fetchone()[0]

print(f"✅ 云数据库现有：")
print(f"   - {cloud_post_count} 条帖子")
print(f"   - {cloud_analysis_count} 条分析")

# Close connections
local_conn.close()
cloud_conn.close()

print("\n" + "=" * 60)
print("✅ 迁移完成！")
print("=" * 60)
print("\n接下来的步骤：")
print("1. 在本地测试：python3 diagnose.py")
print("2. 在 Streamlit Cloud 中设置 Secrets (SQLITE_CLOUD_URL)")
print("3. 访问 Streamlit Cloud 应用验证数据")
