"""
Pytest configuration and fixtures for unit tests.
"""
import pytest
import os
import sys
from datetime import datetime, date, time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Mock external dependencies before any imports that depend on them
mock_crawl4ai = MagicMock()
mock_crawl4ai.AsyncWebCrawler = MagicMock()
mock_crawl4ai.BrowserConfig = MagicMock()
mock_crawl4ai.CrawlerRunConfig = MagicMock()
sys.modules['crawl4ai'] = mock_crawl4ai

# Mock anthropic
mock_anthropic = MagicMock()
mock_anthropic.Anthropic = MagicMock()
mock_anthropic.APIError = Exception
sys.modules['anthropic'] = mock_anthropic

# Mock mailchimp_marketing
mock_mailchimp = MagicMock()
mock_mailchimp.Client = MagicMock()
mock_mailchimp.api_client = MagicMock()
mock_mailchimp.api_client.ApiClientError = Exception
sys.modules['mailchimp_marketing'] = mock_mailchimp
sys.modules['mailchimp_marketing.api_client'] = mock_mailchimp.api_client

# Set test environment variables before importing application modules
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-api-key")
os.environ.setdefault("MAILCHIMP_API_KEY", "test-mailchimp-key")
os.environ.setdefault("MAILCHIMP_SERVER_PREFIX", "us1")
os.environ.setdefault("MAILCHIMP_LIST_ID", "test-list-id")
os.environ.setdefault("MAILCHIMP_REPLY_TO", "test@example.com")
os.environ.setdefault("MANAGER_EMAIL", "manager@example.com")
os.environ.setdefault("ENVIRONMENT", "testing")


# =============================================================================
# Settings Fixtures
# =============================================================================

@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    from config.settings import Settings

    # Create settings with test values
    with patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://test:test@localhost/testdb",
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "MAILCHIMP_API_KEY": "test-mc-key-us1",
        "MAILCHIMP_SERVER_PREFIX": "us1",
        "MAILCHIMP_LIST_ID": "test-list-123",
        "MAILCHIMP_REPLY_TO": "test@example.com",
        "MANAGER_EMAIL": "manager@example.com",
        "BRIGHT_DATA_API_KEY": "test-bright-data-key",
        "BRIGHT_DATA_CUSTOMER_ID": "test-customer-id",
        "ENVIRONMENT": "testing",
        "LOG_LEVEL": "DEBUG",
    }):
        settings = Settings()
        yield settings


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture
def mock_database():
    """Create a mock database instance."""
    from database.connection import Database

    db = MagicMock(spec=Database)
    db.execute = AsyncMock(return_value="OK")
    db.fetch = AsyncMock(return_value=[])
    db.fetchrow = AsyncMock(return_value=None)
    db.fetchval = AsyncMock(return_value=None)
    db.health_check = AsyncMock(return_value=True)
    db._pool = MagicMock()
    return db


@pytest.fixture
def mock_db_pool():
    """Create a mock database pool."""
    pool = MagicMock()
    pool.acquire = MagicMock()
    pool.close = AsyncMock()
    return pool


# =============================================================================
# Model Fixtures
# =============================================================================

@pytest.fixture
def sample_scraped_content():
    """Create sample scraped content for testing."""
    from database.models import ScrapedContent, FilterStatus

    return ScrapedContent(
        id=1,
        url="https://example.com/article-1",
        url_hash="abc123",
        source_name="test_source",
        source_type="news",
        source_platform="website",
        title="Test Article Title",
        content="This is test content for the article. It contains enough text to pass validation.",
        image_url="https://example.com/image.jpg",
        author="Test Author",
        published_at=datetime(2024, 1, 15, 10, 30, 0),
        county="nash",
        summary="A brief summary of the test article",
        content_category="news",
        sentiment="positive",
        sentiment_score=0.8,
        is_event=False,
        event_date=None,
        event_time=None,
        event_location=None,
        filter_status=FilterStatus.PENDING,
        filter_reason=None,
        scraped_at=datetime(2024, 1, 15, 10, 0, 0),
        filtered_at=None,
        created_at=datetime(2024, 1, 15, 10, 0, 0),
        updated_at=datetime(2024, 1, 15, 10, 0, 0)
    )


@pytest.fixture
def sample_approved_content():
    """Create sample approved content for testing."""
    from database.models import ApprovedContent

    return ApprovedContent(
        id=1,
        title="Community Event Announcement",
        summary="Join us for the annual community festival this weekend.",
        url="https://example.com/event",
        source_name="local_news",
        county="nash",
        category="event",
        is_event=True,
        event_date="2024-01-20",
        event_time="14:00",
        event_location="Downtown Park",
        content="Full content of the community event announcement goes here with all the details."
    )


@pytest.fixture
def sample_filter_result():
    """Create sample filter result for testing."""
    from database.models import FilterResult, FilterStatus

    return FilterResult(
        decision=FilterStatus.APPROVED,
        reason="Positive community event announcement",
        sentiment="positive",
        sentiment_score=0.85,
        is_event=True,
        event_date="2024-01-20",
        event_time="14:00",
        event_location="Downtown Park",
        category="event",
        county="nash",
        summary="Annual community festival happening this weekend"
    )


@pytest.fixture
def sample_newsletter():
    """Create sample newsletter for testing."""
    from database.models import Newsletter, NewsletterStatus

    return Newsletter(
        id=1,
        newsletter_id="nl-2024-01-15",
        subject_line="This Week in Twin County",
        top_story_content="<div>Top story content</div>",
        top_story_source_id=1,
        html_content="<html><body>Newsletter content</body></html>",
        plain_text_content="Newsletter plain text",
        total_items=10,
        nash_county_items=5,
        edgecombe_county_items=3,
        wilson_county_items=2,
        event_count=4,
        mailchimp_campaign_id="camp-123",
        mailchimp_campaign_web_id="web-456",
        status=NewsletterStatus.DRAFT,
        preview_sent_to=None,
        preview_sent_at=None,
        scheduled_for=None,
        sent_at=None,
        recipients_count=None,
        opens_count=None,
        clicks_count=None,
        created_at=datetime(2024, 1, 15, 8, 0, 0),
        updated_at=datetime(2024, 1, 15, 8, 0, 0)
    )


# =============================================================================
# Scraper Fixtures
# =============================================================================

@pytest.fixture
def sample_scraped_item():
    """Create sample scraped item for testing."""
    from scrapers.base_scraper import ScrapedItem

    return ScrapedItem(
        url="https://example.com/article",
        content="Test article content with enough text to be valid.",
        source_name="test_source",
        source_type="news",
        source_platform="website",
        title="Test Article",
        image_url="https://example.com/image.jpg",
        author="Test Author",
        published_at=datetime(2024, 1, 15),
        county="nash"
    )


@pytest.fixture
def sample_news_source():
    """Create sample news source configuration."""
    from config.sources import NewsSource, County

    return NewsSource(
        name="test_news",
        display_name="Test News Source",
        url="https://testnews.com",
        county=County.NASH,
        article_selector="article",
        title_selector="h1",
        content_selector=".article-content",
        date_selector=".date",
        is_active=True
    )


@pytest.fixture
def sample_council_source():
    """Create sample council source configuration."""
    from config.sources import CouncilSource, County

    return CouncilSource(
        name="test_council",
        display_name="Test Town Council",
        url="https://testtown.gov/council",
        county=County.NASH,
        minutes_selector="a[href*='minute']",
        is_active=True
    )


@pytest.fixture
def sample_social_source():
    """Create sample social source configuration."""
    from config.sources import SocialSource, County

    return SocialSource(
        name="test_restaurant",
        display_name="Test Restaurant",
        platform="facebook",
        account_id="TestRestaurant",
        county=County.NASH,
        is_active=True
    )


# =============================================================================
# HTTP/API Fixtures
# =============================================================================

@pytest.fixture
def mock_httpx_client():
    """Create mock httpx async client."""
    client = AsyncMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    return client


@pytest.fixture
def mock_anthropic_client():
    """Create mock Anthropic client."""
    client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text='{"decision": "approved", "reason": "test", "sentiment": "positive", "sentiment_score": 0.8, "is_event": false, "category": "news", "summary": "test summary"}')]
    client.messages.create = MagicMock(return_value=mock_message)
    return client


@pytest.fixture
def mock_mailchimp_client():
    """Create mock Mailchimp client."""
    client = MagicMock()
    client.campaigns.create = MagicMock(return_value={"id": "camp-123", "web_id": "web-456"})
    client.campaigns.set_content = MagicMock()
    client.campaigns.send = MagicMock()
    client.campaigns.send_test_email = MagicMock()
    client.campaigns.schedule = MagicMock()
    client.ping.get = MagicMock()
    client.reports.get_campaign_report = MagicMock(return_value={
        "emails_sent": 100,
        "opens": {"opens_total": 50, "unique_opens": 40, "open_rate": 0.4},
        "clicks": {"clicks_total": 20, "unique_subscriber_clicks": 15, "click_rate": 0.15},
        "unsubscribed": 1
    })
    client.lists.get_list = MagicMock(return_value={
        "name": "Test List",
        "stats": {
            "member_count": 500,
            "unsubscribe_count": 10,
            "campaign_count": 25,
            "avg_open_rate": 0.35,
            "avg_click_rate": 0.12
        }
    })
    return client


# =============================================================================
# FastAPI Test Client Fixture
# =============================================================================

@pytest.fixture
def test_app():
    """Create test FastAPI application."""
    from fastapi.testclient import TestClient
    from api.app import create_app

    # Create app without starting background tasks
    app = create_app()
    return TestClient(app)


# =============================================================================
# Helper Functions
# =============================================================================

def create_mock_record(data: Dict[str, Any]):
    """Create a mock database record that acts like asyncpg Record."""
    record = MagicMock()
    record.__getitem__ = lambda self, key: data[key]
    record.get = lambda key, default=None: data.get(key, default)
    record.keys = lambda: data.keys()
    record.values = lambda: data.values()
    record.items = lambda: data.items()

    # Make it iterable
    def _iter(self):
        return iter(data.items())
    record.__iter__ = _iter

    # Support dict() conversion
    def to_dict(self):
        return dict(data)
    record.__dict__.update(data)

    return record


@pytest.fixture
def mock_record_factory():
    """Factory fixture for creating mock database records."""
    return create_mock_record
