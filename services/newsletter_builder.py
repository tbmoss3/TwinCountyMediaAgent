"""
Newsletter builder service - assembles and sends newsletters.
"""
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from database.connection import Database
from database.repositories.content_repository import ContentRepository
from database.repositories.newsletter_repository import NewsletterRepository
from database.models import NewsletterCreate, NewsletterStatus
from services.content_generator import ContentGeneratorService
from services.mailchimp_service import MailchimpService
from config.settings import get_settings

logger = logging.getLogger(__name__)


class NewsletterBuilderService:
    """Service for building and sending newsletters."""

    def __init__(self, db: Database):
        """
        Initialize newsletter builder.

        Args:
            db: Database instance
        """
        self.db = db
        self.settings = get_settings()
        self.content_repo = ContentRepository(db)
        self.newsletter_repo = NewsletterRepository(db)
        self.generator = ContentGeneratorService()
        self.mailchimp = MailchimpService()

        # Setup Jinja2 template environment
        template_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True
        )

    async def build_newsletter(self) -> Optional[int]:
        """
        Build newsletter from approved content.

        Returns:
            Newsletter ID if successful, None otherwise
        """
        try:
            logger.info("Building newsletter...")

            # Get approved content from the past week
            approved_content = await self.content_repo.get_approved_content(
                days=self.settings.content_lookback_days,
                exclude_used=True
            )

            if not approved_content:
                logger.warning("No approved content available for newsletter")
                return None

            # Get upcoming events
            events = await self.content_repo.get_approved_events(days_ahead=14)

            # Generate newsletter content
            generated = await self.generator.generate_newsletter_content(
                approved_content,
                events
            )

            # Get top story URL for the read more link
            top_story_url = ""
            if generated.top_story_source_id:
                top_story_item = next(
                    (c for c in approved_content if c.id == generated.top_story_source_id),
                    None
                )
                if top_story_item:
                    top_story_url = top_story_item.url

            # Render HTML template
            html_content = self._render_template(
                subject_line=generated.subject_line,
                top_story_title=generated.top_story_title,
                top_story_content=generated.top_story_html,
                top_story_url=top_story_url,
                news_links_content=generated.news_links_html,
                calendar_content=generated.calendar_html
            )

            # Create newsletter record
            newsletter_data = NewsletterCreate(
                subject_line=generated.subject_line,
                top_story_content=generated.top_story_html,
                top_story_source_id=generated.top_story_source_id or None,
                html_content=html_content,
                plain_text_content=self._generate_plain_text(approved_content, events),
                total_items=generated.total_items,
                nash_county_items=generated.nash_count,
                edgecombe_county_items=generated.edgecombe_count,
                wilson_county_items=generated.wilson_count,
                event_count=generated.event_count
            )

            newsletter_id = await self.newsletter_repo.create(newsletter_data)

            # Link content to newsletter
            for i, content in enumerate(approved_content):
                section = "top_story" if content.id == generated.top_story_source_id else "news_links"
                await self.newsletter_repo.link_content(
                    newsletter_id, content.id, section, i
                )

            for i, event in enumerate(events):
                await self.newsletter_repo.link_content(
                    newsletter_id, event.id, "calendar", i
                )

            logger.info(f"Newsletter {newsletter_id} built successfully")
            return newsletter_id

        except Exception as e:
            logger.error(f"Error building newsletter: {e}")
            raise

    async def build_and_send_preview(self) -> Optional[int]:
        """
        Build newsletter and send preview to manager.

        Returns:
            Newsletter ID if successful
        """
        # Build the newsletter
        newsletter_id = await self.build_newsletter()

        if not newsletter_id:
            logger.warning("No newsletter to preview")
            return None

        # Get the newsletter
        newsletter = await self.newsletter_repo.get_by_id(newsletter_id)

        try:
            # Create Mailchimp campaign
            campaign = await self.mailchimp.create_campaign(
                subject_line=newsletter.subject_line,
                preview_text="Your weekly roundup of local news and events from Nash, Edgecombe, and Wilson counties",
                html_content=newsletter.html_content
            )

            # Send test email to manager
            await self.mailchimp.send_test_email(
                campaign["campaign_id"],
                [self.settings.manager_email]
            )

            # Update newsletter status
            await self.newsletter_repo.update_status(
                newsletter_id,
                NewsletterStatus.PREVIEW_SENT,
                mailchimp_campaign_id=campaign["campaign_id"],
                mailchimp_campaign_web_id=campaign.get("web_id"),
                preview_sent_to=self.settings.manager_email,
                preview_sent_at=datetime.now()
            )

            logger.info(f"Newsletter preview sent to {self.settings.manager_email}")
            return newsletter_id

        except Exception as e:
            logger.error(f"Error sending preview: {e}")
            # Update status to failed
            await self.newsletter_repo.update_status(
                newsletter_id,
                NewsletterStatus.FAILED
            )
            raise

    async def send_newsletter(self, newsletter_id: int) -> bool:
        """
        Send a newsletter that's been previewed.

        Args:
            newsletter_id: ID of newsletter to send

        Returns:
            True if successful
        """
        newsletter = await self.newsletter_repo.get_by_id(newsletter_id)

        if not newsletter:
            logger.error(f"Newsletter {newsletter_id} not found")
            return False

        if not newsletter.mailchimp_campaign_id:
            logger.error(f"Newsletter {newsletter_id} has no Mailchimp campaign")
            return False

        try:
            await self.mailchimp.send_campaign(newsletter.mailchimp_campaign_id)

            await self.newsletter_repo.update_status(
                newsletter_id,
                NewsletterStatus.SENT,
                sent_at=datetime.now()
            )

            logger.info(f"Newsletter {newsletter_id} sent successfully")
            return True

        except Exception as e:
            logger.error(f"Error sending newsletter: {e}")
            await self.newsletter_repo.update_status(
                newsletter_id,
                NewsletterStatus.FAILED
            )
            return False

    def _render_template(
        self,
        subject_line: str,
        top_story_title: str,
        top_story_content: str,
        top_story_url: str,
        news_links_content: str,
        calendar_content: str
    ) -> str:
        """Render the newsletter HTML template."""
        template = self.jinja_env.get_template("newsletter_base.html")

        return template.render(
            subject_line=subject_line,
            newsletter_date=datetime.now().strftime("%B %d, %Y"),
            top_story_title=top_story_title,
            top_story_content=top_story_content,
            top_story_url=top_story_url,
            news_links_content=news_links_content,
            calendar_content=calendar_content,
            current_year=datetime.now().year
        )

    def _generate_plain_text(self, content: list, events: list) -> str:
        """Generate plain text version of newsletter."""
        lines = [
            "TWIN COUNTY WEEKLY",
            "Your Community Connection",
            datetime.now().strftime("%B %d, %Y"),
            "",
            "=" * 50,
            ""
        ]

        if content:
            lines.append("LOCAL NEWS & UPDATES")
            lines.append("-" * 30)
            for item in content[:10]:
                lines.append(f"\n* {item.title or 'News'}")
                lines.append(f"  {item.summary}")
                lines.append(f"  Read more: {item.url}")
            lines.append("")

        if events:
            lines.append("COMMUNITY CALENDAR")
            lines.append("-" * 30)
            for event in events[:10]:
                date_str = event.event_date or "TBA"
                time_str = event.event_time or ""
                lines.append(f"\n* {date_str} {time_str}")
                lines.append(f"  {event.title or event.summary}")
                if event.event_location:
                    lines.append(f"  Location: {event.event_location}")
            lines.append("")

        lines.extend([
            "=" * 50,
            "",
            "Serving Nash, Edgecombe & Wilson Counties",
            "Unsubscribe: *|UNSUB|*"
        ])

        return "\n".join(lines)
