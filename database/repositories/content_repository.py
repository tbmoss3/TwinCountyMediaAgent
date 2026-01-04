"""
Repository for scraped content CRUD operations.
"""
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional

from database.connection import Database
from database.models import (
    ScrapedContent,
    ScrapedContentCreate,
    FilterResult,
    FilterStatus,
    ApprovedContent
)

logger = logging.getLogger(__name__)


class ContentRepository:
    """Repository for scraped content operations."""

    def __init__(self, db: Database):
        """
        Initialize repository.

        Args:
            db: Database instance
        """
        self.db = db

    @staticmethod
    def compute_url_hash(url: str) -> str:
        """Compute SHA256 hash of URL for deduplication."""
        normalized = url.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def url_exists(self, url: str) -> bool:
        """Check if URL already exists in database."""
        url_hash = self.compute_url_hash(url)
        query = "SELECT EXISTS(SELECT 1 FROM scraped_content WHERE url_hash = $1)"
        return await self.db.fetchval(query, url_hash)

    async def create(self, content: ScrapedContentCreate) -> int:
        """
        Create a new scraped content record.

        Args:
            content: Content to create

        Returns:
            ID of created record
        """
        query = """
        INSERT INTO scraped_content (
            url, url_hash, source_name, source_type, source_platform,
            title, content, image_url, author, published_at, county
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (url_hash) DO NOTHING
        RETURNING id
        """
        result = await self.db.fetchval(
            query,
            content.url,
            content.url_hash,
            content.source_name,
            content.source_type,
            content.source_platform,
            content.title,
            content.content,
            content.image_url,
            content.author,
            content.published_at,
            content.county
        )
        return result

    async def create_many(self, contents: List[ScrapedContentCreate]) -> dict:
        """
        Create multiple content records.

        Returns:
            Dict with counts of new and duplicate items
        """
        new_count = 0
        duplicate_count = 0

        for content in contents:
            result = await self.create(content)
            if result:
                new_count += 1
            else:
                duplicate_count += 1

        return {"new": new_count, "duplicate": duplicate_count}

    async def get_by_id(self, content_id: int) -> Optional[ScrapedContent]:
        """Get content by ID."""
        query = "SELECT * FROM scraped_content WHERE id = $1"
        row = await self.db.fetchrow(query, content_id)
        return ScrapedContent(**dict(row)) if row else None

    async def get_pending_content(self, limit: int = 100) -> List[ScrapedContent]:
        """Get content pending filtering."""
        query = """
        SELECT * FROM scraped_content
        WHERE filter_status = 'pending'
        ORDER BY scraped_at DESC
        LIMIT $1
        """
        rows = await self.db.fetch(query, limit)
        return [ScrapedContent(**dict(row)) for row in rows]

    async def update_filter_result(
        self,
        content_id: int,
        result: FilterResult
    ) -> None:
        """Update content with filter results."""
        query = """
        UPDATE scraped_content SET
            filter_status = $2,
            filter_reason = $3,
            sentiment = $4,
            sentiment_score = $5,
            is_event = $6,
            event_date = $7,
            event_time = $8,
            event_location = $9,
            content_category = $10,
            county = COALESCE($11, county),
            summary = $12,
            filtered_at = NOW(),
            updated_at = NOW()
        WHERE id = $1
        """
        await self.db.execute(
            query,
            content_id,
            result.decision.value,
            result.reason,
            result.sentiment,
            result.sentiment_score,
            result.is_event,
            result.event_date,
            result.event_time,
            result.event_location,
            result.category,
            result.county,
            result.summary
        )

    async def get_approved_content(
        self,
        days: int = 7,
        exclude_used: bool = True
    ) -> List[ApprovedContent]:
        """
        Get approved content for newsletter.

        Args:
            days: Number of days to look back
            exclude_used: Exclude content already used in newsletters
        """
        cutoff = datetime.now() - timedelta(days=days)

        if exclude_used:
            query = """
            SELECT sc.* FROM scraped_content sc
            LEFT JOIN newsletter_content_links ncl ON sc.id = ncl.content_id
            WHERE sc.filter_status = 'approved'
            AND sc.scraped_at >= $1
            AND ncl.id IS NULL
            ORDER BY sc.scraped_at DESC
            """
        else:
            query = """
            SELECT * FROM scraped_content
            WHERE filter_status = 'approved'
            AND scraped_at >= $1
            ORDER BY scraped_at DESC
            """

        rows = await self.db.fetch(query, cutoff)
        return [
            ApprovedContent(
                id=row['id'],
                title=row['title'],
                summary=row['summary'] or '',
                url=row['url'],
                source_name=row['source_name'],
                county=row['county'],
                category=row['content_category'] or 'news',
                is_event=row['is_event'],
                event_date=str(row['event_date']) if row['event_date'] else None,
                event_time=str(row['event_time']) if row['event_time'] else None,
                event_location=row['event_location'],
                content=row['content']
            )
            for row in rows
        ]

    async def get_approved_events(self, days_ahead: int = 30) -> List[ApprovedContent]:
        """Get upcoming events."""
        today = datetime.now().date()
        future = today + timedelta(days=days_ahead)

        query = """
        SELECT * FROM scraped_content
        WHERE filter_status = 'approved'
        AND is_event = TRUE
        AND event_date >= $1
        AND event_date <= $2
        ORDER BY event_date ASC, event_time ASC
        """
        rows = await self.db.fetch(query, today, future)
        return [
            ApprovedContent(
                id=row['id'],
                title=row['title'],
                summary=row['summary'] or '',
                url=row['url'],
                source_name=row['source_name'],
                county=row['county'],
                category=row['content_category'] or 'event',
                is_event=True,
                event_date=str(row['event_date']) if row['event_date'] else None,
                event_time=str(row['event_time']) if row['event_time'] else None,
                event_location=row['event_location'],
                content=row['content']
            )
            for row in rows
        ]

    async def get_stats(self) -> dict:
        """Get content statistics."""
        query = """
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE filter_status = 'pending') as pending,
            COUNT(*) FILTER (WHERE filter_status = 'approved') as approved,
            COUNT(*) FILTER (WHERE filter_status = 'rejected') as rejected,
            COUNT(*) FILTER (WHERE is_event = TRUE) as events,
            COUNT(*) FILTER (WHERE county = 'nash') as nash,
            COUNT(*) FILTER (WHERE county = 'edgecombe') as edgecombe,
            COUNT(*) FILTER (WHERE county = 'wilson') as wilson
        FROM scraped_content
        """
        row = await self.db.fetchrow(query)
        return dict(row)
