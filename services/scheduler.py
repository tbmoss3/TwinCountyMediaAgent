"""
Scheduler service for periodic tasks using APScheduler.
"""
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.base import JobLookupError

from database.connection import Database
from config.settings import get_settings

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for scheduling newsletter and scraping tasks."""

    def __init__(self, db: Database):
        """
        Initialize scheduler service.

        Args:
            db: Database instance
        """
        self.db = db
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler()

        # Track pending newsletter for delayed send (loaded from DB on start)
        self._pending_newsletter_id: Optional[int] = None

    async def _load_state(self) -> None:
        """Load scheduler state from database."""
        try:
            query = "SELECT value FROM system_state WHERE key = 'scheduler'"
            row = await self.db.fetchrow(query)
            if row:
                state = row['value'] if isinstance(row['value'], dict) else json.loads(row['value'])
                self._pending_newsletter_id = state.get('pending_newsletter_id')
                if self._pending_newsletter_id:
                    logger.info(f"Restored pending newsletter ID from database: {self._pending_newsletter_id}")
        except Exception as e:
            logger.warning(f"Failed to load scheduler state: {e}")

    async def _save_state(self) -> None:
        """Save scheduler state to database."""
        try:
            state = json.dumps({'pending_newsletter_id': self._pending_newsletter_id})
            query = """
                UPDATE system_state SET value = $1::jsonb, updated_at = NOW()
                WHERE key = 'scheduler'
            """
            await self.db.execute(query, state)
            logger.debug(f"Saved scheduler state: pending_newsletter_id={self._pending_newsletter_id}")
        except Exception as e:
            logger.warning(f"Failed to save scheduler state: {e}")

    def start(self):
        """Start the scheduler with all configured jobs."""
        # Map day names to cron format
        day_map = {
            "monday": "mon", "tuesday": "tue", "wednesday": "wed",
            "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun"
        }
        day_of_week = day_map.get(self.settings.newsletter_day.lower(), "thu")

        # 1. Newsletter generation job (e.g., Thursday 8:00 AM)
        self.scheduler.add_job(
            self._generate_and_preview_newsletter,
            CronTrigger(
                day_of_week=day_of_week,
                hour=self.settings.newsletter_hour,
                minute=self.settings.newsletter_minute
            ),
            id="newsletter_generation",
            name="Generate Weekly Newsletter",
            replace_existing=True
        )

        # 2. Content scraping job (every 6 hours)
        self.scheduler.add_job(
            self._run_content_scraping,
            IntervalTrigger(hours=self.settings.scrape_frequency_hours),
            id="content_scraping",
            name="Scrape Content Sources",
            replace_existing=True
        )

        # 3. Content filtering job (30 minutes after each scraping run)
        self.scheduler.add_job(
            self._run_content_filtering,
            IntervalTrigger(hours=self.settings.scrape_frequency_hours),
            id="content_filtering",
            name="Filter Scraped Content",
            replace_existing=True,
            # Start 30 minutes after the scraping job
            next_run_time=datetime.now() + timedelta(minutes=30)
        )

        self.scheduler.start()

        logger.info(
            f"Scheduler started. Newsletter: {day_of_week} at "
            f"{self.settings.newsletter_hour}:{self.settings.newsletter_minute:02d}. "
            f"Scraping: every {self.settings.scrape_frequency_hours} hours."
        )

    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shutdown")

    async def _generate_and_preview_newsletter(self):
        """Generate newsletter and send preview to manager."""
        logger.info("Starting scheduled newsletter generation...")

        try:
            from services.newsletter_builder import NewsletterBuilderService

            builder = NewsletterBuilderService(self.db)
            newsletter_id = await builder.build_and_send_preview()

            if newsletter_id:
                self._pending_newsletter_id = newsletter_id
                await self._save_state()  # Persist to database

                # Schedule the final send after preview delay
                if self.settings.auto_send_after_preview:
                    send_time = datetime.now() + timedelta(hours=self.settings.preview_delay_hours)
                    self.scheduler.add_job(
                        self._send_pending_newsletter,
                        DateTrigger(run_date=send_time),
                        id="pending_newsletter_send",
                        name="Send Approved Newsletter",
                        replace_existing=True
                    )
                    logger.info(
                        f"Newsletter preview sent. Auto-send scheduled for {send_time}"
                    )
            else:
                logger.warning("No newsletter generated - insufficient content")

        except Exception as e:
            logger.exception(f"Error in scheduled newsletter generation: {e}")

    async def _send_pending_newsletter(self):
        """Send the pending newsletter after preview delay."""
        if not self._pending_newsletter_id:
            logger.warning("No pending newsletter to send")
            return

        logger.info(f"Sending pending newsletter {self._pending_newsletter_id}...")

        try:
            from services.newsletter_builder import NewsletterBuilderService

            builder = NewsletterBuilderService(self.db)
            success = await builder.send_newsletter(self._pending_newsletter_id)

            if success:
                logger.info(f"Newsletter {self._pending_newsletter_id} sent successfully")
            else:
                logger.error(f"Failed to send newsletter {self._pending_newsletter_id}")

            self._pending_newsletter_id = None
            await self._save_state()  # Persist cleared state to database

        except Exception as e:
            logger.exception(f"Error sending pending newsletter: {e}")

    async def _run_content_scraping(self):
        """Execute content scraping from all sources."""
        logger.info("Starting scheduled content scraping...")

        try:
            from services.scraper_orchestrator import ScraperOrchestrator

            orchestrator = ScraperOrchestrator(self.db)
            stats = await orchestrator.run_scrape()

            logger.info(
                f"Scraping complete. Found: {stats['items_found']}, "
                f"New: {stats['items_new']}, Duplicates: {stats['items_duplicate']}"
            )

        except Exception as e:
            logger.exception(f"Error in scheduled scraping: {e}")

    async def _run_content_filtering(self):
        """Filter newly scraped content using Claude."""
        logger.info("Starting scheduled content filtering...")

        try:
            from database.repositories.content_repository import ContentRepository
            from services.content_filter import ContentFilterService

            content_repo = ContentRepository(self.db)
            filter_service = ContentFilterService()

            # Get pending content
            pending = await content_repo.get_pending_content(limit=100)

            if not pending:
                logger.info("No pending content to filter")
                return

            logger.info(f"Filtering {len(pending)} pending items...")

            # Filter content
            results = await filter_service.batch_filter(pending)

            # Update database with results
            for content, result in results:
                await content_repo.update_filter_result(content.id, result)

            approved = sum(1 for _, r in results if r.decision.value == "approved")
            rejected = sum(1 for _, r in results if r.decision.value == "rejected")

            logger.info(f"Filtering complete. Approved: {approved}, Rejected: {rejected}")

        except Exception as e:
            logger.exception(f"Error in scheduled filtering: {e}")

    async def trigger_newsletter_send(self):
        """Manually trigger newsletter send (bypass preview delay)."""
        if self._pending_newsletter_id:
            # Cancel the scheduled job if exists
            try:
                self.scheduler.remove_job("pending_newsletter_send")
            except JobLookupError:
                # Job doesn't exist, that's fine
                pass

            await self._send_pending_newsletter()
        else:
            logger.warning("No pending newsletter to send")

    def get_scheduled_jobs(self) -> list:
        """Get list of scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs

    def get_pending_newsletter_id(self) -> Optional[int]:
        """Get the ID of the pending newsletter."""
        return self._pending_newsletter_id
