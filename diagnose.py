"""
Diagnostic script to identify why Streamlit can't load data.
Run this to see what's happening.
"""

import json
import os
from datetime import datetime
from database import (
    init_db,
    get_available_dates,
    get_posts_with_analysis,
    get_all_subreddits,
)

print("=" * 60)
print("🔍 REDDIT DASHBOARD DIAGNOSTIC")
print("=" * 60)

# Check 1: Database initialization
print("\n[1️⃣] Database Status")
print("-" * 60)
try:
    init_db()
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"❌ Database init failed: {e}")
    exit(1)

# Check 2: Available dates
print("\n[2️⃣] Available Dates in Database")
print("-" * 60)
try:
    dates = get_available_dates()
    if dates:
        print(f"✅ Found {len(dates)} dates")
        for date in dates:
            print(f"   - {date}")
    else:
        print("⚠️  No dates found in database!")
except Exception as e:
    print(f"❌ Error: {e}")

# Check 3: Config file
print("\n[3️⃣] Configuration File (subreddit_config.json)")
print("-" * 60)
try:
    with open("subreddit_config.json") as f:
        config = json.load(f)
        subreddits = config.get("subreddits", [])
        print(f"✅ Config loaded: {len(subreddits)} subreddits")
        for sub in subreddits:
            print(f"   - {sub}")
except Exception as e:
    print(f"❌ Error reading config: {e}")

# Check 4: Subreddit list from database
print("\n[4️⃣] Subreddit List from Database")
print("-" * 60)
try:
    subs = get_all_subreddits()
    print(f"✅ Database loaded: {len(subs)} subreddits")
    for sub in subs:
        print(f"   - {sub}")
except Exception as e:
    print(f"❌ Error: {e}")

# Check 5: Data retrieval test
print("\n[5️⃣] Data Retrieval Test (4.24 with all subreddits)")
print("-" * 60)
try:
    test_date = "2026-04-24"
    test_subs = get_all_subreddits()

    rows = get_posts_with_analysis(fetch_date=test_date, subreddits=test_subs)

    if rows:
        print(f"✅ Retrieved {len(rows)} posts")
        print(f"\n   Sample posts:")
        for row in rows[:5]:
            sentiment = row.get('sentiment', 'N/A') or 'N/A'
            print(f"   - [{row['subreddit']}] {row['title'][:50]}...")
            print(f"     Sentiment: {sentiment}, Score: {row['score']}")
    else:
        print(f"❌ No data returned for date {test_date}")

        # Debug further
        print(f"\n   Debugging with no filters:")
        all_rows = get_posts_with_analysis()
        print(f"   - Total posts in DB: {len(all_rows)}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Check 6: Analysis status
print("\n[6️⃣] Analysis Status")
print("-" * 60)
try:
    import sqlite3
    conn = sqlite3.connect('reddit_monitor.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT fetch_date, COUNT(*) as total,
               COUNT(a.post_id) as analyzed
        FROM posts p
        LEFT JOIN analysis a ON p.post_id = a.post_id
        GROUP BY fetch_date
        ORDER BY fetch_date DESC
    """)

    results = cursor.fetchall()
    print(f"✅ Analysis breakdown:")
    for date, total, analyzed in results[:5]:
        pct = round((analyzed / total * 100), 1) if total > 0 else 0
        print(f"   {date}: {total} posts, {analyzed} analyzed ({pct}%)")

    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("✅ Diagnosis complete!")
print("=" * 60)
