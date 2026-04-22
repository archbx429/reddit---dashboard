"""
APScheduler wrapper — fires fetch + analyse job every day at 10:00 (Asia/Shanghai).
Run this file directly to test the scheduler in isolation.
"""

import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from reddit_fetcher import fetch_all
from analyzer import analyze_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("scheduler")


def run_fetch_and_analyze() -> None:
    """Scheduled job: pull Reddit posts then run AI analysis."""
    logger.info("=== Scheduled job started ===")
    try:
        new_posts = fetch_all()
        logger.info(f"Fetch complete — {new_posts} new posts stored")
    except Exception as e:
        logger.error(f"Fetch failed: {e}", exc_info=True)

    try:
        analysed = analyze_all()
        logger.info(f"Analysis complete — {analysed} posts analysed")
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)

    logger.info("=== Scheduled job finished ===")


def create_scheduler() -> BackgroundScheduler:
    """Create and configure a BackgroundScheduler. Call .start() separately."""
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        run_fetch_and_analyze,
        trigger=CronTrigger(hour=10, minute=0, timezone="Asia/Shanghai"),
        id="daily_reddit_fetch",
        name="Daily Reddit Fetch & Analyse",
        replace_existing=True,
        misfire_grace_time=3600,  # allow up to 1 h late start
    )
    return scheduler


if __name__ == "__main__":
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler running. Next trigger: 10:00 Asia/Shanghai. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped.")
