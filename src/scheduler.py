"""
Post scheduling service for automated LinkedIn publishing.

Uses APScheduler to check for and publish scheduled posts.
"""

from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.database import get_db
from src.linkedin_api import LinkedInAPI
from src.logger import logger


class PostScheduler:
    """Scheduler for automatic post publishing"""

    def __init__(self):
        """Initialize the post scheduler"""
        self.scheduler = BackgroundScheduler()
        self.db = get_db()
        self.linkedin_api = None
        logger.info("Post scheduler initialized")

    def start(self):
        """Start the scheduler"""
        # Check for scheduled posts every minute
        self.scheduler.add_job(
            func=self.check_and_publish_scheduled_posts,
            trigger=IntervalTrigger(minutes=1),
            id='check_scheduled_posts',
            name='Check and publish scheduled posts',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Post scheduler started - checking every minute")

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Post scheduler stopped")

    def check_and_publish_scheduled_posts(self):
        """Check for posts that need to be published and publish them"""
        try:
            # Get posts scheduled for now or earlier
            now = datetime.utcnow()

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, content, hashtags, image_path, scheduled_for
                    FROM posts
                    WHERE is_scheduled = 1
                    AND status = 'approved'
                    AND scheduled_for <= ?
                    AND published_at IS NULL
                    ORDER BY scheduled_for ASC
                """, (now,))

                posts = cursor.fetchall()

            if not posts:
                logger.debug("No scheduled posts to publish")
                return

            logger.info(f"Found {len(posts)} posts to publish")

            # Initialize LinkedIn API if needed
            if not self.linkedin_api:
                self.linkedin_api = LinkedInAPI(db=self.db)

            # Publish each post
            for post in posts:
                post_id = post[0]
                content = post[1]
                hashtags = post[2]
                image_path = post[3]
                scheduled_for = post[4]

                try:
                    logger.info(f"Publishing scheduled post {post_id} (scheduled for {scheduled_for})")

                    # Combine content and hashtags
                    post_text = content
                    if hashtags:
                        post_text += f"\n\n{hashtags}"

                    # Publish the post
                    result = self.linkedin_api.publish_post(
                        text=post_text,
                        post_id=post_id,
                        image_path=image_path
                    )

                    if result:
                        # Update post status
                        with self.db.get_connection() as conn:
                            conn.execute("""
                                UPDATE posts
                                SET is_scheduled = 0,
                                    published_at = ?
                                WHERE id = ?
                            """, (datetime.utcnow(), post_id))

                        logger.info(f"✓ Successfully published scheduled post {post_id}")
                    else:
                        logger.error(f"Failed to publish scheduled post {post_id}")

                except Exception as e:
                    logger.error(f"Error publishing post {post_id}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in scheduled post check: {e}")

    def schedule_post(
        self,
        post_id: int,
        scheduled_time: datetime
    ) -> bool:
        """
        Schedule a post for future publishing.

        Args:
            post_id: Post ID to schedule
            scheduled_time: When to publish the post

        Returns:
            True if scheduled successfully
        """
        try:
            with self.db.get_connection() as conn:
                # Verify post exists and is approved
                cursor = conn.execute(
                    "SELECT id, status FROM posts WHERE id = ?",
                    (post_id,)
                )
                post = cursor.fetchone()

                if not post:
                    logger.error(f"Post {post_id} not found")
                    return False

                if post[1] != 'approved':
                    logger.error(f"Post {post_id} is not approved (status: {post[1]})")
                    return False

                # Update post with schedule info
                conn.execute("""
                    UPDATE posts
                    SET scheduled_for = ?,
                        is_scheduled = 1,
                        updated_at = ?
                    WHERE id = ?
                """, (scheduled_time, datetime.utcnow(), post_id))

            logger.info(f"Post {post_id} scheduled for {scheduled_time}")
            return True

        except Exception as e:
            logger.error(f"Error scheduling post {post_id}: {e}")
            return False

    def unschedule_post(self, post_id: int) -> bool:
        """
        Cancel a scheduled post.

        Args:
            post_id: Post ID to unschedule

        Returns:
            True if unscheduled successfully
        """
        try:
            with self.db.get_connection() as conn:
                conn.execute("""
                    UPDATE posts
                    SET scheduled_for = NULL,
                        is_scheduled = 0,
                        updated_at = ?
                    WHERE id = ?
                """, (datetime.utcnow(), post_id))

            logger.info(f"Post {post_id} unscheduled")
            return True

        except Exception as e:
            logger.error(f"Error unscheduling post {post_id}: {e}")
            return False

    def get_scheduled_posts(self, days_ahead: int = 30):
        """
        Get all posts scheduled within the next N days.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of scheduled posts
        """
        try:
            now = datetime.utcnow()
            future = now + timedelta(days=days_ahead)

            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT
                        p.id, p.content, p.hashtags, p.scheduled_for,
                        p.status, p.image_path,
                        t.title as trend_title
                    FROM posts p
                    LEFT JOIN trends t ON p.trend_id = t.id
                    WHERE p.is_scheduled = 1
                    AND p.scheduled_for >= ?
                    AND p.scheduled_for <= ?
                    AND p.published_at IS NULL
                    ORDER BY p.scheduled_for ASC
                """, (now, future))

                posts = []
                for row in cursor.fetchall():
                    posts.append({
                        'id': row[0],
                        'content': row[1],
                        'hashtags': row[2],
                        'scheduled_for': row[3],
                        'status': row[4],
                        'image_path': row[5],
                        'trend_title': row[6]
                    })

                return posts

        except Exception as e:
            logger.error(f"Error getting scheduled posts: {e}")
            return []


# Global scheduler instance
_scheduler = None


def get_scheduler() -> PostScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = PostScheduler()
    return _scheduler


def start_scheduler():
    """Start the global scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_scheduler():
    """Stop the global scheduler"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None
