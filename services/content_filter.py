"""
Claude AI-powered content filtering and classification.
"""
import asyncio
import json
import logging
from typing import List, Optional, Tuple

import anthropic
from anthropic import AsyncAnthropic
from circuitbreaker import circuit
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config.settings import get_settings
from database.models import ScrapedContent, FilterResult, FilterStatus

logger = logging.getLogger(__name__)


class ContentFilterService:
    """Service for filtering content using Claude AI."""

    FILTER_PROMPT = """You are a content curator for a local community newsletter serving Nash, Edgecombe, and Wilson counties in North Carolina.

Analyze the following content and determine if it should be included in the newsletter.

APPROVAL CRITERIA (INCLUDE if any of these apply):
- Positive sentiment or neutral informational content
- Community events (festivals, fundraisers, openings, concerts, markets, etc.)
- Business announcements (new openings, specials, promotions, grand openings)
- Achievement stories and recognition (awards, graduations, promotions)
- Public meeting notices and civic engagement opportunities
- Health and wellness information
- Educational opportunities
- Local sports achievements
- Community service activities
- Restaurant/bar events and specials
- Chamber of Commerce news
- Economic development news

REJECTION CRITERIA (EXCLUDE if any of these apply):
- Negative news (crime reports, accidents, fatalities, unless commemorative/memorial)
- Political controversy or divisive partisan content
- Complaints, negative reviews, or criticism
- Content older than 14 days (unless it's an upcoming future event)
- Spam, ads without local relevance, or irrelevant content
- National/international news without local connection

CONTENT TO ANALYZE:
Source: {source_name} ({source_type})
Title: {title}
Content: {content}
Published: {published_at}
Current County Tag: {county}

IMPORTANT: Respond with ONLY a valid JSON object (no markdown, no code blocks, no explanation):
{{
    "decision": "approved" or "rejected",
    "reason": "Brief 1-sentence explanation",
    "sentiment": "positive" or "neutral" or "negative",
    "sentiment_score": 0.0 to 1.0 (1.0 = most positive),
    "is_event": true or false,
    "event_date": "YYYY-MM-DD" or null (extract if this is about an event),
    "event_time": "HH:MM" or null (24-hour format if mentioned),
    "event_location": "Location name/address" or null,
    "category": "event" or "news" or "announcement" or "promotion" or "government" or "other",
    "county": "nash" or "edgecombe" or "wilson" or null (confirm or detect county),
    "summary": "One engaging sentence summary suitable for newsletter (max 150 chars)"
}}"""

    def __init__(self):
        """Initialize content filter service."""
        self.settings = get_settings()
        # Use async client for non-blocking API calls
        self.client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)

    def _get_retry_decorator(self):
        """Create retry decorator with settings from config."""
        return retry(
            stop=stop_after_attempt(self.settings.api_retry_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=self.settings.api_retry_min_wait,
                max=self.settings.api_retry_max_wait
            ),
            retry=retry_if_exception_type((
                anthropic.RateLimitError,
                anthropic.APIConnectionError,
                anthropic.InternalServerError,
            )),
            before_sleep=lambda retry_state: logger.warning(
                f"Claude API call failed, retrying in {retry_state.next_action.sleep} seconds..."
            )
        )

    @circuit(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=anthropic.APIError
    )
    async def _call_claude_api(self, prompt: str) -> str:
        """
        Call Claude API with circuit breaker protection.

        Args:
            prompt: The prompt to send to Claude

        Returns:
            Response text from Claude
        """
        message = await self.client.messages.create(
            model=self.settings.claude_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()

    async def filter_content(self, content: ScrapedContent) -> FilterResult:
        """
        Filter a single content item using Claude.

        Args:
            content: Scraped content to filter

        Returns:
            FilterResult with decision and metadata
        """
        try:
            prompt = self.FILTER_PROMPT.format(
                source_name=content.source_name,
                source_type=content.source_type,
                title=content.title or "No title",
                content=content.content[:4000],  # Limit content length
                published_at=content.published_at.isoformat() if content.published_at else "Unknown",
                county=content.county or "Unknown"
            )

            # Call Claude API with retry logic
            retry_decorator = self._get_retry_decorator()

            @retry_decorator
            async def make_api_call():
                return await self._call_claude_api(prompt)

            response_text = await make_api_call()

            # Clean up response if it has markdown code blocks
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            result_data = json.loads(response_text)

            return FilterResult(
                decision=FilterStatus(result_data["decision"]),
                reason=result_data["reason"],
                sentiment=result_data["sentiment"],
                sentiment_score=float(result_data["sentiment_score"]),
                is_event=bool(result_data["is_event"]),
                event_date=result_data.get("event_date"),
                event_time=result_data.get("event_time"),
                event_location=result_data.get("event_location"),
                category=result_data["category"],
                county=result_data.get("county") or content.county,
                summary=result_data["summary"]
            )

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Claude response for content {content.id}: {e}")
            return self._create_error_result(content, f"JSON parse error: {e}")

        except anthropic.APIError as e:
            logger.error(f"Claude API error for content {content.id}: {e}")
            return self._create_error_result(content, f"API error: {e}")

        except Exception as e:
            logger.error(f"Error filtering content {content.id}: {e}")
            return self._create_error_result(content, str(e))

    def _create_error_result(self, content: ScrapedContent, error: str) -> FilterResult:
        """Create a rejection result for errors."""
        return FilterResult(
            decision=FilterStatus.REJECTED,
            reason=f"Error during filtering: {error}",
            sentiment="neutral",
            sentiment_score=0.5,
            is_event=False,
            event_date=None,
            event_time=None,
            event_location=None,
            category="other",
            county=content.county,
            summary=""
        )

    async def batch_filter(
        self,
        contents: List[ScrapedContent],
        max_concurrent: int = 5
    ) -> List[Tuple[ScrapedContent, FilterResult]]:
        """
        Filter multiple content items.

        Args:
            contents: List of ScrapedContent to filter
            max_concurrent: Maximum concurrent API calls

        Returns:
            List of (ScrapedContent, FilterResult) tuples
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def filter_with_semaphore(
            content: ScrapedContent
        ) -> Tuple[ScrapedContent, FilterResult]:
            async with semaphore:
                result = await self.filter_content(content)
                return (content, result)

        tasks = [filter_with_semaphore(c) for c in contents]
        results = await asyncio.gather(*tasks)

        # Log summary
        approved = sum(1 for _, r in results if r.decision == FilterStatus.APPROVED)
        rejected = sum(1 for _, r in results if r.decision == FilterStatus.REJECTED)
        logger.info(f"Batch filter complete: {approved} approved, {rejected} rejected")

        return results

    async def health_check(self) -> bool:
        """
        Check if Claude API is accessible.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Use a minimal test to check API connectivity
            message = await self.client.messages.create(
                model="claude-3-haiku-20240307",  # Use cheapest model for health check
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception as e:
            logger.error(f"Claude API health check failed: {e}")
            return False
