"""
Repository for newsletter CRUD operations.
"""
import logging
from datetime import datetime
from typing import List, Optional

from database.connection import Database
from database.models import Newsletter, NewsletterCreate, NewsletterStatus

logger = logging.getLogger(__name__)


class NewsletterRepository:
    """Repository for newsletter operations."""

    def __init__(self, db: Database):
        """
        Initialize repository.

        Args:
            db: Database instance
        """
        self.db = db

    async def create(self, newsletter: NewsletterCreate) -> int:
        """
        Create a new newsletter record.

        Args:
            newsletter: Newsletter to create

        Returns:
            ID of created record
        """
        query = """
        INSERT INTO sent_newsletters (
            subject_line, top_story_content, top_story_source_id,
            html_content, plain_text_content,
            total_items, nash_county_items, edgecombe_county_items,
            wilson_county_items, event_count
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id
        """
        return await self.db.fetchval(
            query,
            newsletter.subject_line,
            newsletter.top_story_content,
            newsletter.top_story_source_id,
            newsletter.html_content,
            newsletter.plain_text_content,
            newsletter.total_items,
            newsletter.nash_county_items,
            newsletter.edgecombe_county_items,
            newsletter.wilson_county_items,
            newsletter.event_count
        )

    async def get_by_id(self, newsletter_id: int) -> Optional[Newsletter]:
        """Get newsletter by ID."""
        query = "SELECT * FROM sent_newsletters WHERE id = $1"
        row = await self.db.fetchrow(query, newsletter_id)
        return Newsletter(**dict(row)) if row else None

    async def get_latest(self) -> Optional[Newsletter]:
        """Get the most recently created newsletter."""
        query = """
        SELECT * FROM sent_newsletters
        ORDER BY created_at DESC
        LIMIT 1
        """
        row = await self.db.fetchrow(query)
        return Newsletter(**dict(row)) if row else None

    async def get_pending_newsletter(self) -> Optional[Newsletter]:
        """Get newsletter with preview_sent status (awaiting final send)."""
        query = """
        SELECT * FROM sent_newsletters
        WHERE status = 'preview_sent'
        ORDER BY created_at DESC
        LIMIT 1
        """
        row = await self.db.fetchrow(query)
        return Newsletter(**dict(row)) if row else None

    async def update_status(
        self,
        newsletter_id: int,
        status: NewsletterStatus,
        **kwargs
    ) -> None:
        """Update newsletter status and optional fields."""
        updates = ["status = $2", "updated_at = NOW()"]
        params = [newsletter_id, status.value]
        param_idx = 3

        if 'mailchimp_campaign_id' in kwargs:
            updates.append(f"mailchimp_campaign_id = ${param_idx}")
            params.append(kwargs['mailchimp_campaign_id'])
            param_idx += 1

        if 'mailchimp_campaign_web_id' in kwargs:
            updates.append(f"mailchimp_campaign_web_id = ${param_idx}")
            params.append(kwargs['mailchimp_campaign_web_id'])
            param_idx += 1

        if 'preview_sent_to' in kwargs:
            updates.append(f"preview_sent_to = ${param_idx}")
            params.append(kwargs['preview_sent_to'])
            param_idx += 1

        if 'preview_sent_at' in kwargs:
            updates.append(f"preview_sent_at = ${param_idx}")
            params.append(kwargs['preview_sent_at'])
            param_idx += 1

        if 'scheduled_for' in kwargs:
            updates.append(f"scheduled_for = ${param_idx}")
            params.append(kwargs['scheduled_for'])
            param_idx += 1

        if 'sent_at' in kwargs:
            updates.append(f"sent_at = ${param_idx}")
            params.append(kwargs['sent_at'])
            param_idx += 1

        query = f"""
        UPDATE sent_newsletters
        SET {', '.join(updates)}
        WHERE id = $1
        """
        await self.db.execute(query, *params)

    async def update_metrics(
        self,
        newsletter_id: int,
        recipients_count: int,
        opens_count: int,
        clicks_count: int
    ) -> None:
        """Update newsletter metrics from Mailchimp webhook."""
        query = """
        UPDATE sent_newsletters SET
            recipients_count = $2,
            opens_count = $3,
            clicks_count = $4,
            updated_at = NOW()
        WHERE id = $1
        """
        await self.db.execute(
            query,
            newsletter_id,
            recipients_count,
            opens_count,
            clicks_count
        )

    async def link_content(
        self,
        newsletter_id: int,
        content_id: int,
        section: str,
        display_order: int = 0
    ) -> None:
        """Link content to a newsletter."""
        query = """
        INSERT INTO newsletter_content_links (
            newsletter_id, content_id, section, display_order
        ) VALUES ($1, $2, $3, $4)
        ON CONFLICT (newsletter_id, content_id) DO NOTHING
        """
        await self.db.execute(query, newsletter_id, content_id, section, display_order)

    async def get_recent_newsletters(self, limit: int = 10) -> List[Newsletter]:
        """Get recent newsletters."""
        query = """
        SELECT * FROM sent_newsletters
        ORDER BY created_at DESC
        LIMIT $1
        """
        rows = await self.db.fetch(query, limit)
        return [Newsletter(**dict(row)) for row in rows]

    async def get_stats(self) -> dict:
        """Get newsletter statistics."""
        query = """
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'sent') as sent,
            COUNT(*) FILTER (WHERE status = 'preview_sent') as pending_approval,
            AVG(total_items) as avg_items,
            AVG(event_count) as avg_events,
            SUM(recipients_count) as total_recipients,
            SUM(opens_count) as total_opens,
            SUM(clicks_count) as total_clicks
        FROM sent_newsletters
        """
        row = await self.db.fetchrow(query)
        return dict(row)
