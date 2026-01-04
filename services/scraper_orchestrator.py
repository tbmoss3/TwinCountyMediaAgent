"""
Orchestrator for running all scrapers.
"""
import logging
from typing import List, Optional
from datetime import datetime
import uuid

from database.connection import Database
from database.repositories.content_repository import ContentRepository
from database.models import ScrapedContentCreate
from scrapers.news_scraper import NewsScraper
from scrapers.council_scraper import CouncilScraper
from scrapers.social_scraper import BrightDataSocialScraper
from scrapers.base_scraper import ScrapedItem
from config.sources import (
    get_active_news_sources,
    get_active_council_sources,
    get_active_social_sources
)
from config.settings import get_settings

logger = logging.getLogger(__name__)


class ScraperOrchestrator:
    """Orchestrates running all scrapers and storing results."""

    def __init__(self, db: Database):
        """
        Initialize orchestrator.

        Args:
            db: Database instance
        """
        self.db = db
        self.content_repo = ContentRepository(db)
        self.settings = get_settings()

    async def run_scrape(self, source_type: Optional[str] = None) -> dict:
        """
        Run scrapers for specified type or all types.

        Args:
            source_type: Optional filter - 'news', 'social', or 'council'

        Returns:
            Dict with scrape statistics
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now()

        logger.info(f"Starting scrape run {run_id} (type: {source_type or 'all'})")

        stats = {
            "run_id": run_id,
            "started_at": started_at.isoformat(),
            "sources_scraped": 0,
            "items_found": 0,
            "items_new": 0,
            "items_duplicate": 0,
            "errors": []
        }

        try:
            # Run news scrapers
            if source_type is None or source_type == "news":
                news_stats = await self._run_news_scrapers()
                self._merge_stats(stats, news_stats)

            # Run council scrapers
            if source_type is None or source_type == "council":
                if self.settings.enable_council_scraping:
                    council_stats = await self._run_council_scrapers()
                    self._merge_stats(stats, council_stats)

            # Run social scrapers
            if source_type is None or source_type == "social":
                if self.settings.enable_social_scraping and self.settings.social_scraping_enabled:
                    social_stats = await self._run_social_scrapers()
                    self._merge_stats(stats, social_stats)

            # Record the scrape run
            await self._record_scrape_run(
                run_id=run_id,
                source_type=source_type,
                stats=stats
            )

        except Exception as e:
            logger.error(f"Error in scrape run: {e}")
            stats["errors"].append(str(e))

        stats["completed_at"] = datetime.now().isoformat()
        stats["duration_seconds"] = (datetime.now() - started_at).total_seconds()

        logger.info(
            f"Scrape run {run_id} completed. "
            f"Found: {stats['items_found']}, New: {stats['items_new']}, "
            f"Duplicates: {stats['items_duplicate']}"
        )

        return stats

    async def _run_news_scrapers(self) -> dict:
        """Run all news scrapers."""
        stats = {"items_found": 0, "items_new": 0, "items_duplicate": 0, "sources_scraped": 0}

        for source in get_active_news_sources():
            try:
                scraper = NewsScraper(source)
                items = await scraper.scrape()

                if items:
                    result = await self._store_items(items)
                    stats["items_found"] += len(items)
                    stats["items_new"] += result["new"]
                    stats["items_duplicate"] += result["duplicate"]

                stats["sources_scraped"] += 1

            except Exception as e:
                logger.error(f"Error scraping {source.name}: {e}")

        return stats

    async def _run_council_scrapers(self) -> dict:
        """Run all council scrapers."""
        stats = {"items_found": 0, "items_new": 0, "items_duplicate": 0, "sources_scraped": 0}

        for source in get_active_council_sources():
            try:
                scraper = CouncilScraper(source)
                items = await scraper.scrape()

                if items:
                    result = await self._store_items(items)
                    stats["items_found"] += len(items)
                    stats["items_new"] += result["new"]
                    stats["items_duplicate"] += result["duplicate"]

                stats["sources_scraped"] += 1

            except Exception as e:
                logger.error(f"Error scraping {source.name}: {e}")

        return stats

    async def _run_social_scrapers(self) -> dict:
        """Run all social scrapers."""
        stats = {"items_found": 0, "items_new": 0, "items_duplicate": 0, "sources_scraped": 0}

        for source in get_active_social_sources():
            try:
                scraper = BrightDataSocialScraper(source)

                if not scraper.is_configured():
                    logger.warning(f"Skipping {source.name} - Bright Data not configured")
                    continue

                items = await scraper.scrape()

                if items:
                    result = await self._store_items(items)
                    stats["items_found"] += len(items)
                    stats["items_new"] += result["new"]
                    stats["items_duplicate"] += result["duplicate"]

                stats["sources_scraped"] += 1

            except Exception as e:
                logger.error(f"Error scraping {source.name}: {e}")

        return stats

    async def _store_items(self, items: List[ScrapedItem]) -> dict:
        """Store scraped items in database."""
        contents = [
            ScrapedContentCreate(
                url=item.url,
                url_hash=item.url_hash,
                source_name=item.source_name,
                source_type=item.source_type,
                source_platform=item.source_platform,
                title=item.title,
                content=item.content,
                image_url=item.image_url,
                author=item.author,
                published_at=item.published_at,
                county=item.county
            )
            for item in items
        ]

        return await self.content_repo.create_many(contents)

    def _merge_stats(self, main: dict, sub: dict) -> None:
        """Merge sub-stats into main stats."""
        main["sources_scraped"] += sub.get("sources_scraped", 0)
        main["items_found"] += sub.get("items_found", 0)
        main["items_new"] += sub.get("items_new", 0)
        main["items_duplicate"] += sub.get("items_duplicate", 0)

    async def _record_scrape_run(self, run_id: str, source_type: Optional[str], stats: dict) -> None:
        """Record scrape run in database."""
        query = """
        INSERT INTO scrape_runs (
            run_id, source_type, status,
            items_found, items_new, items_duplicate,
            completed_at
        ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """
        await self.db.execute(
            query,
            run_id,
            source_type,
            "completed",
            stats["items_found"],
            stats["items_new"],
            stats["items_duplicate"]
        )
