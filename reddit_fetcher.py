"""
Fetch posts (and top comments) from Reddit public JSON API.
No API key required — uses the open /<subreddit>/<sort>.json endpoint.
"""

import json
import os
import time
from datetime import datetime
from typing import List

import requests

from database import init_db, insert_post, update_post_comments, get_all_subreddits, init_default_subreddits

# Default subreddits
DEFAULT_SUBREDDITS = ["bambulab", "EufyMakeOfficial", "snapmaker"]

# Initialize database with defaults on first run
init_default_subreddits(DEFAULT_SUBREDDITS)

# Load subreddits from database
SUBREDDITS = get_all_subreddits(default=DEFAULT_SUBREDDITS)
CATEGORIES = ["hot", "new"]
LIMIT = 20

# Seconds to sleep between list-page requests (be polite to Reddit)
REQUEST_DELAY = 1.5
# Seconds to sleep between individual comment requests (shorter, fewer per run)
COMMENT_DELAY = 0.8
# Only fetch comments when post body is shorter than this threshold (chars)
SHORT_TEXT_THRESHOLD = 100
# Number of top-level comments to keep
COMMENT_LIMIT = 8

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_subreddit(subreddit: str, category: str = "hot") -> List[dict]:
    """
    Fetch up to LIMIT posts from a subreddit via the public JSON endpoint.
    Returns a list of raw post dicts from Reddit's 'children' array.
    Retries up to 3 times on failure.
    """
    url = f"https://www.reddit.com/r/{subreddit}/{category}.json?limit={LIMIT}"
    max_retries = 3

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            if posts:
                print(f"       [尝试 {attempt+1}/{max_retries}] ✅ 成功获取 {len(posts)} 条帖子")
                return posts
            else:
                print(f"       [尝试 {attempt+1}/{max_retries}] ⚠️ 获取 0 条帖子")
                return []
        except requests.exceptions.HTTPError as e:
            print(f"       [尝试 {attempt+1}/{max_retries}] ❌ HTTP错误: {e.response.status_code}")
        except requests.exceptions.ConnectionError as e:
            print(f"       [尝试 {attempt+1}/{max_retries}] ❌ 连接错误 - 重试中...")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        except requests.exceptions.Timeout:
            print(f"       [尝试 {attempt+1}/{max_retries}] ⏱️  超时 - 重试中...")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        except Exception as e:
            print(f"       [尝试 {attempt+1}/{max_retries}] ❌ 错误: {str(e)[:80]}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    print(f"       ❌ 最终失败：无法从 r/{subreddit}/{category} 获取数据")
    return []


def fetch_post_comments(subreddit: str, post_id: str) -> List[str]:
    """
    Fetch top-level comments for a single post, sorted by top score.
    Returns a list of comment body strings (cleaned, up to COMMENT_LIMIT).
    """
    url = (
        f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
        f"?limit={COMMENT_LIMIT}&sort=top&depth=1"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # data is [post_listing, comments_listing]
        if not isinstance(data, list) or len(data) < 2:
            return []
        children = data[1].get("data", {}).get("children", [])
        comments = []
        for child in children:
            if child.get("kind") != "t1":  # t1 = comment
                continue
            body = (child.get("data", {}).get("body") or "").strip()
            if body and body not in ("[removed]", "[deleted]"):
                comments.append(body[:300])
            if len(comments) >= COMMENT_LIMIT:
                break
        return comments
    except Exception as e:
        print(f"[Fetcher] Error fetching comments for {post_id}: {e}")
        return []


def process_posts(
    raw_posts: List[dict],
    subreddit: str,
    category: str,
    fetch_date: str,
) -> int:
    """
    Normalise and store raw Reddit post objects.
    For posts with little/no body text, also fetch and store top comments.
    Returns count of newly inserted rows.
    """
    saved = 0
    for item in raw_posts:
        d = item.get("data", {})
        post_id = d.get("id", "").strip()
        if not post_id:
            continue

        selftext = d.get("selftext", "") or ""
        if selftext in ("[removed]", "[deleted]"):
            selftext = ""

        record = {
            "post_id": post_id,
            "subreddit": subreddit,
            "title": (d.get("title") or "").strip(),
            "selftext": selftext[:2000],
            "score": int(d.get("score") or 0),
            "upvote_ratio": float(d.get("upvote_ratio") or 0.0),
            "num_comments": int(d.get("num_comments") or 0),
            "author": d.get("author", "") or "",
            "created_utc": int(d.get("created_utc") or 0),
            "fetch_date": fetch_date,
            "category": category,
        }

        is_new = insert_post(record)
        if is_new:
            saved += 1
            # For image/video/link posts with little body text, pull top comments
            # so the analyser has real user reactions to work with
            if len(selftext) < SHORT_TEXT_THRESHOLD and int(d.get("num_comments") or 0) > 0:
                time.sleep(COMMENT_DELAY)
                comments = fetch_post_comments(subreddit, post_id)
                if comments:
                    update_post_comments(post_id, fetch_date, comments)
                    print(
                        f"[Fetcher]   ↳ {post_id}: fetched {len(comments)} comments "
                        f"(short body: {len(selftext)} chars)"
                    )

    return saved


def fetch_all(subreddits: List[str] = None) -> int:
    """
    Iterate over all (subreddit, category) combinations, fetch posts and store them.

    Args:
        subreddits: Optional list of subreddit names to fetch. If None, loads from config.

    Returns:
        The total number of newly inserted posts.
    """
    init_db()
    fetch_date = datetime.now().strftime("%Y-%m-%d")
    total_new = 0

    # Use provided subreddits list or reload from config
    if subreddits is None:
        current_subreddits = get_all_subreddits(default=DEFAULT_SUBREDDITS)
    else:
        current_subreddits = subreddits
    print(f"[Fetcher] 加载的频道列表: {current_subreddits}")

    for subreddit in current_subreddits:
        for category in CATEGORIES:
            print(f"[Fetcher] 正在爬取: r/{subreddit}/{category} ...")
            raw = fetch_subreddit(subreddit, category)
            new_count = process_posts(raw, subreddit, category, fetch_date)
            print(f"[Fetcher]   ✓ 获取 {len(raw)} 条, 保存 {new_count} 条新帖子")
            total_new += new_count
            time.sleep(REQUEST_DELAY)

    print(f"[Fetcher] ========== 爬取完成 ==========")
    print(f"[Fetcher] 总共新增: {total_new} 条帖子")
    print(f"[Fetcher] 频道数: {len(current_subreddits)}")
    return total_new


if __name__ == "__main__":
    fetch_all()
