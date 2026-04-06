import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import load_config
from app.models import SessionLocal
from app.sync.gerrit import sync_gerrit
from app.sync.github import sync_github

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def run_sync():
    config = load_config()
    db = SessionLocal()
    try:
        for instance in config.get("gerrit_instances", []):
            try:
                sync_gerrit(db, instance)
            except Exception as e:
                logger.error(f"Gerrit sync failed for {instance['name']}: {e}")

        for instance in config.get("github_instances", []):
            try:
                sync_github(db, instance)
            except Exception as e:
                logger.error(f"GitHub sync failed for {instance['name']}: {e}")
    finally:
        db.close()


def start_scheduler():
    config = load_config()
    interval = config.get("sync_interval_minutes", 30)
    scheduler.add_job(run_sync, "interval", minutes=interval, id="sync_all")
    scheduler.start()
    logger.info(f"Scheduler started (interval: {interval}m)")
