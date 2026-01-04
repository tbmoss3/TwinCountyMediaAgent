"""
Newsletter content generation using Claude AI.
"""
import logging
from typing import List, Optional
from dataclasses import dataclass

import anthropic

from config.settings import get_settings
from database.models import ApprovedContent

logger = logging.getLogger(__name__)


@dataclass
class GeneratedContent:
    """Generated newsletter content sections."""
    top_story_html: str
    top_story_title: str
    top_story_source_id: int
    news_links_html: str
    calendar_html: str
    subject_line: str
    total_items: int
    event_count: int
    nash_count: int
    edgecombe_count: int
    wilson_count: int


class ContentGeneratorService:
    """Service for generating newsletter content using Claude AI."""

    TOP_STORY_PROMPT = """You are writing for a local community newsletter serving Nash, Edgecombe, and Wilson counties in North Carolina.

Write an engaging 200-word highlight piece about this story. Use a professional, upbeat, and community-focused voice.

STORY DETAILS:
Title: {title}
Source: {source_name}
Summary: {summary}
Full Content: {content}

GUIDELINES:
- Write exactly 200 words (give or take 20 words)
- Start with an engaging hook that draws readers in
- Highlight the community benefit, impact, or interest
- Include relevant details (who, what, when, where)
- End with a forward-looking statement or soft call to action
- Maintain a warm, neighborly, professional tone
- Do NOT include a headline - just the body text
- Do NOT use phrases like "This week" or "Recently" as the first word

Write the story now (just the body text, no headline):"""

    SUBJECT_LINE_PROMPT = """Generate a compelling email subject line for a local community newsletter.

Top Story: {top_story_title}
Number of Events: {event_count}
Counties: Nash, Edgecombe, Wilson (NC)

Requirements:
- Maximum 50 characters
- Include a local/community feel
- Create curiosity or excitement without clickbait
- Don't use ALL CAPS or excessive punctuation
- Don't start with "Newsletter:" or similar

Just return the subject line text, nothing else."""

    def __init__(self):
        """Initialize content generator service."""
        self.settings = get_settings()
        self.client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

    async def generate_newsletter_content(
        self,
        approved_content: List[ApprovedContent],
        events: List[ApprovedContent]
    ) -> GeneratedContent:
        """
        Generate all newsletter content sections.

        Args:
            approved_content: List of approved content items
            events: List of upcoming events

        Returns:
            GeneratedContent with all sections
        """
        # Select top story (highest potential impact)
        top_story = self._select_top_story(approved_content)

        # Generate top story content
        top_story_html = ""
        if top_story:
            top_story_html = await self._generate_top_story(top_story)

        # Generate news links section
        news_links_html = self._generate_news_links_section(
            [c for c in approved_content if c.id != (top_story.id if top_story else None)]
        )

        # Generate calendar section
        calendar_html = self._generate_calendar_section(events)

        # Generate subject line
        subject_line = await self._generate_subject_line(
            top_story.title if top_story else "Community News",
            len(events)
        )

        # Count by county
        nash_count = sum(1 for c in approved_content if c.county == "nash")
        edgecombe_count = sum(1 for c in approved_content if c.county == "edgecombe")
        wilson_count = sum(1 for c in approved_content if c.county == "wilson")

        return GeneratedContent(
            top_story_html=top_story_html,
            top_story_title=top_story.title if top_story else "",
            top_story_source_id=top_story.id if top_story else 0,
            news_links_html=news_links_html,
            calendar_html=calendar_html,
            subject_line=subject_line,
            total_items=len(approved_content),
            event_count=len(events),
            nash_count=nash_count,
            edgecombe_count=edgecombe_count,
            wilson_count=wilson_count
        )

    def _select_top_story(self, content: List[ApprovedContent]) -> Optional[ApprovedContent]:
        """Select the most impactful story for the top spot."""
        if not content:
            return None

        # Prioritize by category and content quality
        priority_order = ["event", "announcement", "news", "promotion", "government", "other"]

        # Sort by priority and content length (longer = more detailed)
        def score(item):
            category_score = priority_order.index(item.category) if item.category in priority_order else 99
            length_score = -len(item.content)  # Negative because we want longer first
            has_title = 0 if item.title else 1
            return (has_title, category_score, length_score)

        sorted_content = sorted(content, key=score)
        return sorted_content[0] if sorted_content else None

    async def _generate_top_story(self, content: ApprovedContent) -> str:
        """Generate the featured top story content."""
        try:
            prompt = self.TOP_STORY_PROMPT.format(
                title=content.title or "Local Story",
                source_name=content.source_name,
                summary=content.summary,
                content=content.content[:4000]
            )

            message = self.client.messages.create(
                model=self.settings.claude_model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            story_text = message.content[0].text.strip()

            # Wrap in HTML
            return f"""
            <div class="top-story-body">
                <p>{story_text}</p>
            </div>
            """

        except Exception as e:
            logger.error(f"Error generating top story: {e}")
            # Fallback to summary
            return f"""
            <div class="top-story-body">
                <p>{content.summary}</p>
            </div>
            """

    def _generate_news_links_section(self, items: List[ApprovedContent]) -> str:
        """Generate the aggregated news links section."""
        # Group by county
        by_county = {
            "nash": [],
            "edgecombe": [],
            "wilson": [],
            "regional": []
        }

        for item in items:
            county = item.county or "regional"
            if county in by_county:
                by_county[county].append(item)
            else:
                by_county["regional"].append(item)

        html_parts = []

        county_names = {
            "nash": "Nash County",
            "edgecombe": "Edgecombe County",
            "wilson": "Wilson County",
            "regional": "Regional News"
        }

        for county, county_items in by_county.items():
            if not county_items:
                continue

            html_parts.append(f'<h3 style="color: #2c5530; margin-top: 20px;">{county_names[county]}</h3>')
            html_parts.append('<ul style="list-style: none; padding: 0; margin: 0;">')

            for item in county_items[:5]:  # Limit per county
                title = item.title or item.summary[:60] + "..."
                html_parts.append(f'''
                <li style="margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #e8ebe9;">
                    <a href="{item.url}" style="color: #1a365d; font-weight: 600; text-decoration: none; font-size: 16px;">
                        {title}
                    </a>
                    <p style="margin: 5px 0 0 0; color: #4a5568; font-size: 14px; line-height: 1.5;">
                        {item.summary}
                    </p>
                    <span style="color: #a0aec0; font-size: 12px;">Source: {item.source_name}</span>
                </li>
                ''')

            html_parts.append('</ul>')

        return '\n'.join(html_parts)

    def _generate_calendar_section(self, events: List[ApprovedContent]) -> str:
        """Generate the community calendar section."""
        if not events:
            return '<p style="color: #718096; font-style: italic;">No upcoming events this week.</p>'

        # Sort events by date
        sorted_events = sorted(
            [e for e in events if e.event_date],
            key=lambda x: x.event_date
        )

        html_parts = ['<table style="width: 100%; border-collapse: collapse;">']
        html_parts.append('''
            <thead>
                <tr style="background: #2c5530; color: white;">
                    <th style="padding: 12px 10px; text-align: left; font-size: 13px;">Date</th>
                    <th style="padding: 12px 10px; text-align: left; font-size: 13px;">Time</th>
                    <th style="padding: 12px 10px; text-align: left; font-size: 13px;">Event</th>
                    <th style="padding: 12px 10px; text-align: left; font-size: 13px;">Location</th>
                </tr>
            </thead>
            <tbody>
        ''')

        for i, event in enumerate(sorted_events[:10]):  # Limit to 10 events
            # Parse date for display
            try:
                from datetime import datetime
                date_obj = datetime.strptime(event.event_date, "%Y-%m-%d")
                day_display = date_obj.strftime("%a, %b %d")
            except:
                day_display = event.event_date or "TBA"

            row_bg = "#faf8f5" if i % 2 == 1 else "#ffffff"
            event_title = event.title or event.summary[:50]

            html_parts.append(f'''
            <tr style="border-bottom: 1px solid #e8ebe9; background: {row_bg};">
                <td style="padding: 12px 10px; font-size: 14px;">{day_display}</td>
                <td style="padding: 12px 10px; font-size: 14px;">{event.event_time or "TBA"}</td>
                <td style="padding: 12px 10px; font-size: 14px;">
                    <a href="{event.url}" style="color: #1a365d; text-decoration: none;">
                        {event_title}
                    </a>
                </td>
                <td style="padding: 12px 10px; font-size: 14px; color: #4a5568;">{event.event_location or "See details"}</td>
            </tr>
            ''')

        html_parts.append('</tbody></table>')
        return '\n'.join(html_parts)

    async def _generate_subject_line(self, top_story_title: str, event_count: int) -> str:
        """Generate an engaging subject line."""
        try:
            prompt = self.SUBJECT_LINE_PROMPT.format(
                top_story_title=top_story_title,
                event_count=event_count
            )

            message = self.client.messages.create(
                model=self.settings.claude_model,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )

            subject = message.content[0].text.strip()
            # Ensure it's not too long
            if len(subject) > 60:
                subject = subject[:57] + "..."

            return subject

        except Exception as e:
            logger.error(f"Error generating subject line: {e}")
            return "Your Twin County Weekly Update"
