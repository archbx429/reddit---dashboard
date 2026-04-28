"""
Analyse Reddit posts with the Google Gemini API (google-genai SDK).
- Rate limit: max 5 requests / second
- Retry: up to 3 attempts with exponential back-off
- API key read from .env (GEMINI_API_KEY)
"""

import json
import os
import time
from typing import Optional, List

from dotenv import load_dotenv
from google import genai
from google.genai import types

from database import get_posts_needing_analysis, insert_analysis, get_failed_analysis_posts

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = "gemini-2.5-flash"

MAX_RPS = 5
MIN_INTERVAL = 1.0 / MAX_RPS   # 0.2 s between calls
MAX_RETRIES = 3

_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. "
                "Copy .env.example to .env and fill in your Gemini API key."
            )
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _detect_media_type(post: dict) -> str:
    """Detect if post is video, image, or link based on content."""
    body = (post.get("selftext") or "").strip()
    title = post.get("title", "").lower()

    # Check title for media indicators
    if "video" in title:
        return "[视频]"
    if "image" in title or "pic" in title or "photo" in title:
        return "[图片]"

    # If no body text but has comments, likely media post
    if not body and post.get("num_comments", 0) > 0:
        return "[媒体]"

    return ""


def _build_prompt(post: dict) -> str:
    title = post.get("title", "")
    body = (post.get("selftext") or "").strip()[:800]
    subreddit = post.get("subreddit", "")
    author = post.get("author", "")

    content_section = (
        f"【正文】\n{body}"
        if body
        else "(该帖子为纯媒体内容，无文字正文)"
    )

    return f"""你是一个 Reddit 社区内容分析助手。请基于帖子标题和正文分析该帖子，以纯 JSON 格式返回结果（不要加 markdown 代码块）。

子版块: r/{subreddit}
标题: {title}
作者: {author}

{content_section}

返回格式（严格 JSON，不要多余文字）:
{{
  "sentiment": "positive 或 negative 或 neutral",
  "content_type": "bug_report 或 feature_request 或 showcase 或 help 或 discussion 或 other",
  "user_type": "hobbyist 或 artist_creator 或 maker 或 reviewer_influencer 或 small_business 或 print_farm 或 unknown",
  "user_type_confidence": "high 或 medium 或 low",
  "key_topics": ["关键词1", "关键词2", "关键词3"],
  "summary": "中文摘要，50字以内，可包含【标签】如【创客】【商家】等"
}}

user_type 分类规则（仅基于作者名、标题和正文，不使用评论内容）：

【hobbyist】爱好者 - 个人娱乐/学习为主
  - 关键词：my first / hobby / for fun / gift / personal project / learning / just wanted / let me share
  - 特征：首次接触，个人兴趣，非商业目的
  - 示例标题：My first print! / Built this as a hobby / Learning to design

【artist_creator】艺术创作者 - 艺术/设计/创意工作
  - 关键词：art / sculpture / design / creative / aesthetic / gallery / visual / artistic
  - 特征：强调创意和艺术价值，展示个人作品
  - 示例标题：Designed this / Creative project / Artistic print

【maker】创客/改造者 - 技术改造/模组/功能性
  - 关键词：mod / upgrade / modification / enclosure / mount / functional / remix / hack / custom / OpenSCAD / 3D design
  - 特征：强调技术改造、功能优化、DIY精神
  - 示例标题：Built a custom enclosure / Modified my printer / 3D designed this mount

【reviewer_influencer】评测/影响者 - 产品评测/视频内容创作
  - 关键词：review / unboxing / compared / comparison / review after / my channel / video / content creator / vs / benchmark
  - 特征：系统评测、详细对比、内容创作导向
  - 示例标题：Full review / Unboxing / Compared with

【small_business】小商家 - 销售/商业化生产
  - 关键词：sell / selling / Etsy / shop / business / customer / order / commission / print for / profit / income
  - 特征：涉及销售、客户、订单等商业活动
  - 示例标题：Started selling / Taking commissions / New Etsy shop

【print_farm】大规模生产 - 批量/工业级生产
  - 关键词：farm / factory / fleet / multiple printers / batch production / mass production / production line
  - 特征：多台设备、批量生产、规模化运营
  - 示例标题：Our print farm / 30 printers / Mass production setup

【unknown】无法分类 - 仅当内容过于简短或完全无法判断时使用

**关键判断原则**：
- 仅使用作者名、标题、正文内容进行判断，完全忽略用户评论
- 当信号明确时设置为 high confidence，多个信号重合时 high，部分匹配时 medium，信号模糊时 low
- 当内容无法清晰判断时，优先选择与内容最接近的类型而非 unknown
- summary 可在末尾添加【标签】如【创客】【商家】【艺术】等强化用户类型"""


def _parse_response(content: str) -> Optional[dict]:
    """Strip markdown fences and parse JSON from model output."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner).strip()
    try:
        result = json.loads(text)
        result["key_topics"] = result.get("key_topics", [])[:3]
        result["sentiment"] = result.get("sentiment", "neutral")
        result["content_type"] = result.get("content_type", "other")
        result["user_type"] = result.get("user_type", "unknown")
        result["user_type_confidence"] = result.get("user_type_confidence", "medium")
        result["summary"] = str(result.get("summary", ""))[:100]
        return result
    except json.JSONDecodeError:
        return None


def _default_analysis(post: Optional[dict] = None) -> dict:
    """Default analysis when model fails; note media type and check official account."""
    media_type = _detect_media_type(post) if post else ""
    user_type = _check_official_account(post) if post else None
    user_type = user_type or "unknown"
    return {
        "sentiment": "neutral",
        "content_type": "other",
        "user_type": user_type,
        "user_type_confidence": "low",
        "key_topics": [],
        "summary": f"{media_type}分析失败" if media_type else "分析失败",
    }


def _check_official_account(post: dict) -> Optional[str]:
    """Quick check if post author is an official account. Return 'official' or None."""
    OFFICIAL_ACCOUNTS = {
        "BambuLab", "bambulab",
        "EufyMakeOfficial", "eufymakeofficial",
        "Snapmaker", "snapmaker",
    }
    author = (post.get("author") or "").strip()
    if author in OFFICIAL_ACCOUNTS:
        return "official"
    return None


def analyze_post(post: dict) -> Optional[dict]:
    """
    Call Gemini API to analyse a single post (body + comments).
    Returns parsed dict on success, None on unrecoverable failure.
    """
    # If official account detected, pre-set the user_type
    official_check = _check_official_account(post)

    prompt = _build_prompt(post)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = _get_client().models.generate_content(
                model=MODEL,
                contents=prompt,
            )
            content = resp.text or ""
            result = _parse_response(content)
            if result is not None:
                # Override user_type if official account detected
                if official_check:
                    result["user_type"] = official_check
                return result
            # JSON parse failed - log more context
            print(
                f"[Analyzer] JSON parse failed for {post['post_id']} "
                f"(attempt {attempt}/{MAX_RETRIES})"
            )
            print(f"           Raw response: {content[:200]}")
        except Exception as e:
            error_str = str(e).lower()
            if "resource" in error_str or "quota" in error_str or "rate" in error_str:
                wait = 2 ** attempt
                print(f"[Analyzer] Rate limit hit for {post['post_id']}, waiting {wait}s ...")
                time.sleep(wait)
                continue
            print(f"[Analyzer] API error for {post['post_id']} (attempt {attempt}): {str(e)[:100]}")

        if attempt < MAX_RETRIES:
            time.sleep(2 ** attempt)

    return None


def analyze_all() -> int:
    """
    Analyse every post that has no analysis record yet.
    Respects MAX_RPS rate limit and retries on failure.
    Returns count of successfully analysed posts.
    """
    posts = get_posts_needing_analysis()
    if not posts:
        print("[Analyzer] No posts need analysis.")
        return 0

    print(f"[Analyzer] Starting analysis of {len(posts)} posts ...")
    success = 0

    for i, post in enumerate(posts, start=1):
        t_start = time.monotonic()

        result = analyze_post(post)
        if result is not None:
            insert_analysis(post["post_id"], result)
            success += 1
            has_comments = bool(post.get("top_comments"))
            media_tag = _detect_media_type(post)
            print(
                f"[Analyzer] [{i}/{len(posts)}] OK — "
                f"{post['post_id']} | {result['sentiment']} | "
                f"{'💬' if has_comments else '  '} {media_tag}{post.get('title', '')[:40]}"
            )
        else:
            default = _default_analysis(post)
            insert_analysis(post["post_id"], default)
            print(f"[Analyzer] [{i}/{len(posts)}] FAILED — {post['post_id']}: {default['summary']}")

        elapsed = time.monotonic() - t_start
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)

    print(f"[Analyzer] Done. {success}/{len(posts)} posts analysed successfully.")
    return success


def analyze_failed_posts(fetch_date: Optional[str] = None) -> int:
    """
    Re-analyse posts with failed analysis (summary is '分析失败' or empty).
    If fetch_date is provided, only re-analyse posts from that date.
    Respects MAX_RPS rate limit and retries on failure.
    Returns count of successfully re-analysed posts.
    """
    posts = get_failed_analysis_posts(fetch_date)
    if not posts:
        print(f"[Analyzer] No failed posts to re-analyse{f' for {fetch_date}' if fetch_date else ''}.")
        return 0

    print(f"[Analyzer] Re-analysing {len(posts)} failed posts{f' from {fetch_date}' if fetch_date else ''} ...")
    success = 0

    for i, post in enumerate(posts, start=1):
        t_start = time.monotonic()

        result = analyze_post(post)
        if result is not None:
            insert_analysis(post["post_id"], result)
            success += 1
            has_comments = bool(post.get("top_comments"))
            media_tag = _detect_media_type(post)
            print(
                f"[Analyzer] [{i}/{len(posts)}] OK — "
                f"{post['post_id']} | {result['sentiment']} | "
                f"{'💬' if has_comments else '  '} {media_tag}{post.get('title', '')[:40]}"
            )
        else:
            default = _default_analysis(post)
            insert_analysis(post["post_id"], default)
            print(f"[Analyzer] [{i}/{len(posts)}] FAILED — {post['post_id']}: {default['summary']}")

        elapsed = time.monotonic() - t_start
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)

    print(f"[Analyzer] Done. {success}/{len(posts)} posts re-analysed successfully.")
    return success


if __name__ == "__main__":
    analyze_all()
