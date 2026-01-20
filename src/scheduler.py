"""Scheduler module for periodic post generation"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class PostScheduler:
    """Handles scheduling of post generation tasks"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
    
    def start(self):
        """Start the scheduler"""
        logger.info("Starting scheduler")
        self.scheduler.start()
    
    def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping scheduler")
        self.scheduler.shutdown()
    
    def schedule_post_generation(self, job_func, hour=9, minute=0):
        """Schedule daily post generation at specified time"""
        self.scheduler.add_job(
            job_func,
            CronTrigger(hour=hour, minute=minute),
            id="generate_posts",
            name="Generate daily posts"
        )
        logger.info(f"Scheduled post generation at {hour:02d}:{minute:02d}")
