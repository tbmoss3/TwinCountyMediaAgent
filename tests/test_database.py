"""
Unit tests for database module (models, connection, repositories).
"""
import pytest
from datetime import datetime, date, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib


class TestDatabaseModels:
    """Test cases for Pydantic database models."""

    def test_filter_status_enum_values(self):
        """Test FilterStatus enum values."""
        from database.models import FilterStatus

        assert FilterStatus.PENDING.value == "pending"
        assert FilterStatus.APPROVED.value == "approved"
        assert FilterStatus.REJECTED.value == "rejected"

    def test_newsletter_status_enum_values(self):
        """Test NewsletterStatus enum values."""
        from database.models import NewsletterStatus

        assert NewsletterStatus.DRAFT.value == "draft"
        assert NewsletterStatus.PREVIEW_SENT.value == "preview_sent"
        assert NewsletterStatus.SCHEDULED.value == "scheduled"
        assert NewsletterStatus.SENT.value == "sent"
        assert NewsletterStatus.FAILED.value == "failed"

    def test_scrape_run_status_enum_values(self):
        """Test ScrapeRunStatus enum values."""
        from database.models import ScrapeRunStatus

        assert ScrapeRunStatus.RUNNING.value == "running"
        assert ScrapeRunStatus.COMPLETED.value == "completed"
        assert ScrapeRunStatus.FAILED.value == "failed"

    def test_scraped_content_create_model(self):
        """Test ScrapedContentCreate model creation."""
        from database.models import ScrapedContentCreate

        content = ScrapedContentCreate(
            url="https://example.com/article",
            url_hash="abc123",
            source_name="test_source",
            source_type="news",
            content="Test content"
        )

        assert content.url == "https://example.com/article"
        assert content.url_hash == "abc123"
        assert content.source_name == "test_source"
        assert content.title is None  # Optional field

    def test_scraped_content_model_with_all_fields(self, sample_scraped_content):
        """Test ScrapedContent model with all fields populated."""
        assert sample_scraped_content.id == 1
        assert sample_scraped_content.url == "https://example.com/article-1"
        assert sample_scraped_content.title == "Test Article Title"
        assert sample_scraped_content.sentiment == "positive"
        assert sample_scraped_content.sentiment_score == 0.8

    def test_filter_result_model(self, sample_filter_result):
        """Test FilterResult model creation."""
        from database.models import FilterStatus

        assert sample_filter_result.decision == FilterStatus.APPROVED
        assert sample_filter_result.sentiment == "positive"
        assert sample_filter_result.is_event is True
        assert sample_filter_result.event_date == "2024-01-20"

    def test_newsletter_create_model(self):
        """Test NewsletterCreate model creation."""
        from database.models import NewsletterCreate

        newsletter = NewsletterCreate(
            subject_line="Weekly Update",
            html_content="<html>Content</html>",
            total_items=10
        )

        assert newsletter.subject_line == "Weekly Update"
        assert newsletter.html_content == "<html>Content</html>"
        assert newsletter.total_items == 10

    def test_newsletter_model(self, sample_newsletter):
        """Test Newsletter model with all fields."""
        from database.models import NewsletterStatus

        assert sample_newsletter.id == 1
        assert sample_newsletter.status == NewsletterStatus.DRAFT
        assert sample_newsletter.total_items == 10

    def test_approved_content_model(self, sample_approved_content):
        """Test ApprovedContent model creation."""
        assert sample_approved_content.id == 1
        assert sample_approved_content.is_event is True
        assert sample_approved_content.event_location == "Downtown Park"

    def test_scrape_run_create_model(self):
        """Test ScrapeRunCreate model creation."""
        from database.models import ScrapeRunCreate

        run = ScrapeRunCreate(
            source_name="test_source",
            source_type="news"
        )

        assert run.source_name == "test_source"
        assert run.source_type == "news"

    def test_scrape_run_model(self):
        """Test ScrapeRun model with all fields."""
        from database.models import ScrapeRun, ScrapeRunStatus

        run = ScrapeRun(
            id=1,
            run_id="run-123",
            source_name="test_source",
            source_type="news",
            status=ScrapeRunStatus.COMPLETED,
            items_found=50,
            items_new=45,
            items_duplicate=5,
            started_at=datetime(2024, 1, 15, 10, 0, 0),
            completed_at=datetime(2024, 1, 15, 10, 5, 0)
        )

        assert run.status == ScrapeRunStatus.COMPLETED
        assert run.items_found == 50


class TestDatabaseConnection:
    """Test cases for Database connection management."""

    def test_database_initialization(self):
        """Test Database class initialization."""
        from database.connection import Database

        db = Database(
            database_url="postgresql://test:test@localhost/testdb",
            min_size=2,
            max_size=10
        )

        assert db.database_url == "postgresql://test:test@localhost/testdb"
        assert db.min_size == 2
        assert db.max_size == 10
        assert db._pool is None

    @pytest.mark.asyncio
    async def test_database_connect(self):
        """Test Database connect method."""
        from database.connection import Database

        db = Database(database_url="postgresql://test:test@localhost/testdb")

        # Mock asyncpg.create_pool
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value="PostgreSQL 14.0")

        # Setup context manager for acquire
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("asyncpg.create_pool", new=AsyncMock(return_value=mock_pool)):
            await db.connect()
            assert db._pool is not None

    @pytest.mark.asyncio
    async def test_database_disconnect(self, mock_database):
        """Test Database disconnect method."""
        from database.connection import Database

        db = Database(database_url="postgresql://test:test@localhost/testdb")
        mock_pool = MagicMock()
        mock_pool.close = AsyncMock()
        db._pool = mock_pool

        await db.disconnect()

        mock_pool.close.assert_called_once()
        assert db._pool is None

    @pytest.mark.asyncio
    async def test_database_disconnect_no_pool(self):
        """Test Database disconnect when no pool exists."""
        from database.connection import Database

        db = Database(database_url="postgresql://test:test@localhost/testdb")
        # Should not raise
        await db.disconnect()

    def test_database_pool_property_raises_when_not_initialized(self):
        """Test pool property raises when not initialized."""
        from database.connection import Database

        db = Database(database_url="postgresql://test:test@localhost/testdb")

        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            _ = db.pool

    def test_database_pool_property_returns_pool(self):
        """Test pool property returns pool when initialized."""
        from database.connection import Database

        db = Database(database_url="postgresql://test:test@localhost/testdb")
        db._pool = MagicMock()

        assert db.pool is db._pool

    @pytest.mark.asyncio
    async def test_database_execute(self, mock_database):
        """Test Database execute method."""
        mock_database.execute.return_value = "INSERT 0 1"

        result = await mock_database.execute("INSERT INTO test VALUES ($1)", 1)

        assert result == "INSERT 0 1"
        mock_database.execute.assert_called_once_with("INSERT INTO test VALUES ($1)", 1)

    @pytest.mark.asyncio
    async def test_database_fetch(self, mock_database):
        """Test Database fetch method."""
        mock_database.fetch.return_value = [{"id": 1, "name": "test"}]

        result = await mock_database.fetch("SELECT * FROM test")

        assert len(result) == 1
        assert result[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_database_fetchrow(self, mock_database):
        """Test Database fetchrow method."""
        mock_database.fetchrow.return_value = {"id": 1, "name": "test"}

        result = await mock_database.fetchrow("SELECT * FROM test WHERE id = $1", 1)

        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_database_fetchval(self, mock_database):
        """Test Database fetchval method."""
        mock_database.fetchval.return_value = 42

        result = await mock_database.fetchval("SELECT COUNT(*) FROM test")

        assert result == 42

    @pytest.mark.asyncio
    async def test_database_health_check_healthy(self, mock_database):
        """Test Database health_check returns True when healthy."""
        mock_database.health_check.return_value = True

        result = await mock_database.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_database_health_check_unhealthy(self, mock_database):
        """Test Database health_check returns False when unhealthy."""
        mock_database.health_check.return_value = False

        result = await mock_database.health_check()

        assert result is False

    def test_get_database_raises_when_not_initialized(self):
        """Test get_database raises when database not initialized."""
        from database.connection import get_database, _db
        import database.connection

        # Ensure _db is None
        original_db = database.connection._db
        database.connection._db = None

        try:
            with pytest.raises(RuntimeError, match="Database not initialized"):
                get_database()
        finally:
            database.connection._db = original_db

    def test_init_database(self, mock_settings):
        """Test init_database creates Database instance."""
        from database.connection import init_database
        import database.connection

        original_db = database.connection._db

        try:
            db = init_database(mock_settings)

            assert db is not None
            assert db.database_url == mock_settings.database_url
        finally:
            database.connection._db = original_db


class TestContentRepository:
    """Test cases for ContentRepository."""

    def test_compute_url_hash(self):
        """Test URL hash computation."""
        from database.repositories.content_repository import ContentRepository

        url = "https://example.com/article"
        expected_hash = hashlib.sha256("https://example.com/article".encode()).hexdigest()

        result = ContentRepository.compute_url_hash(url)

        assert result == expected_hash

    def test_compute_url_hash_normalizes_url(self):
        """Test URL hash computation normalizes URLs."""
        from database.repositories.content_repository import ContentRepository

        url1 = "https://EXAMPLE.COM/ARTICLE"
        url2 = "  https://example.com/article  "

        hash1 = ContentRepository.compute_url_hash(url1)
        hash2 = ContentRepository.compute_url_hash(url2)

        assert hash1 == hash2

    @pytest.mark.asyncio
    async def test_url_exists_true(self, mock_database):
        """Test url_exists returns True when URL exists."""
        from database.repositories.content_repository import ContentRepository

        mock_database.fetchval.return_value = True
        repo = ContentRepository(mock_database)

        result = await repo.url_exists("https://example.com/article")

        assert result is True
        mock_database.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_url_exists_false(self, mock_database):
        """Test url_exists returns False when URL doesn't exist."""
        from database.repositories.content_repository import ContentRepository

        mock_database.fetchval.return_value = False
        repo = ContentRepository(mock_database)

        result = await repo.url_exists("https://example.com/new-article")

        assert result is False

    @pytest.mark.asyncio
    async def test_create_content(self, mock_database):
        """Test create method inserts content."""
        from database.repositories.content_repository import ContentRepository
        from database.models import ScrapedContentCreate

        mock_database.fetchval.return_value = 1
        repo = ContentRepository(mock_database)

        content = ScrapedContentCreate(
            url="https://example.com/article",
            url_hash="abc123",
            source_name="test_source",
            source_type="news",
            content="Test content"
        )

        result = await repo.create(content)

        assert result == 1
        mock_database.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_many_content(self, mock_database):
        """Test create_many method inserts multiple contents."""
        from database.repositories.content_repository import ContentRepository
        from database.models import ScrapedContentCreate

        # First call returns 1 (new), second returns None (duplicate)
        mock_database.fetchval.side_effect = [1, None, 2]
        repo = ContentRepository(mock_database)

        contents = [
            ScrapedContentCreate(url="https://example.com/1", url_hash="h1",
                               source_name="test", source_type="news", content="c1"),
            ScrapedContentCreate(url="https://example.com/2", url_hash="h2",
                               source_name="test", source_type="news", content="c2"),
            ScrapedContentCreate(url="https://example.com/3", url_hash="h3",
                               source_name="test", source_type="news", content="c3"),
        ]

        result = await repo.create_many(contents)

        assert result["new"] == 2
        assert result["duplicate"] == 1

    @pytest.mark.asyncio
    async def test_get_by_id(self, mock_database, mock_record_factory):
        """Test get_by_id returns content."""
        from database.repositories.content_repository import ContentRepository

        mock_record = mock_record_factory({
            "id": 1,
            "url": "https://example.com/article",
            "url_hash": "abc123",
            "source_name": "test_source",
            "source_type": "news",
            "source_platform": "website",
            "title": "Test Title",
            "content": "Test content",
            "image_url": None,
            "author": None,
            "published_at": datetime(2024, 1, 15),
            "county": "nash",
            "summary": "Summary",
            "content_category": "news",
            "sentiment": "positive",
            "sentiment_score": 0.8,
            "is_event": False,
            "event_date": None,
            "event_time": None,
            "event_location": None,
            "filter_status": "pending",
            "filter_reason": None,
            "scraped_at": datetime(2024, 1, 15),
            "filtered_at": None,
            "created_at": datetime(2024, 1, 15),
            "updated_at": datetime(2024, 1, 15)
        })

        mock_database.fetchrow.return_value = mock_record
        repo = ContentRepository(mock_database)

        result = await repo.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.url == "https://example.com/article"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_database):
        """Test get_by_id returns None when not found."""
        from database.repositories.content_repository import ContentRepository

        mock_database.fetchrow.return_value = None
        repo = ContentRepository(mock_database)

        result = await repo.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_pending_content(self, mock_database):
        """Test get_pending_content returns pending content."""
        from database.repositories.content_repository import ContentRepository

        mock_database.fetch.return_value = []
        repo = ContentRepository(mock_database)

        result = await repo.get_pending_content(limit=50)

        assert result == []
        mock_database.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_filter_result(self, mock_database, sample_filter_result):
        """Test update_filter_result updates content."""
        from database.repositories.content_repository import ContentRepository

        repo = ContentRepository(mock_database)

        await repo.update_filter_result(1, sample_filter_result)

        mock_database.execute.assert_called_once()
        call_args = mock_database.execute.call_args[0]
        assert "UPDATE scraped_content" in call_args[0]

    @pytest.mark.asyncio
    async def test_get_approved_content(self, mock_database):
        """Test get_approved_content returns approved content."""
        from database.repositories.content_repository import ContentRepository

        mock_database.fetch.return_value = []
        repo = ContentRepository(mock_database)

        result = await repo.get_approved_content(days=7, exclude_used=True)

        assert result == []
        mock_database.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_approved_events(self, mock_database):
        """Test get_approved_events returns upcoming events."""
        from database.repositories.content_repository import ContentRepository

        mock_database.fetch.return_value = []
        repo = ContentRepository(mock_database)

        result = await repo.get_approved_events(days_ahead=30)

        assert result == []
        mock_database.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stats(self, mock_database, mock_record_factory):
        """Test get_stats returns statistics."""
        from database.repositories.content_repository import ContentRepository

        mock_record = mock_record_factory({
            "total": 100,
            "pending": 20,
            "approved": 70,
            "rejected": 10,
            "events": 15,
            "nash": 50,
            "edgecombe": 30,
            "wilson": 20
        })
        mock_database.fetchrow.return_value = mock_record
        repo = ContentRepository(mock_database)

        result = await repo.get_stats()

        assert result["total"] == 100
        assert result["approved"] == 70


class TestNewsletterRepository:
    """Test cases for NewsletterRepository."""

    @pytest.mark.asyncio
    async def test_create_newsletter(self, mock_database):
        """Test create method creates newsletter."""
        from database.repositories.newsletter_repository import NewsletterRepository
        from database.models import NewsletterCreate

        mock_database.fetchval.return_value = 1
        repo = NewsletterRepository(mock_database)

        newsletter = NewsletterCreate(
            subject_line="Weekly Update",
            html_content="<html>Content</html>",
            total_items=10
        )

        result = await repo.create(newsletter)

        assert result == 1
        mock_database.fetchval.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id(self, mock_database, mock_record_factory):
        """Test get_by_id returns newsletter."""
        from database.repositories.newsletter_repository import NewsletterRepository

        mock_record = mock_record_factory({
            "id": 1,
            "newsletter_id": "nl-123",
            "subject_line": "Weekly Update",
            "top_story_content": "<div>Story</div>",
            "top_story_source_id": 1,
            "html_content": "<html>Content</html>",
            "plain_text_content": "Plain text",
            "total_items": 10,
            "nash_county_items": 5,
            "edgecombe_county_items": 3,
            "wilson_county_items": 2,
            "event_count": 4,
            "mailchimp_campaign_id": None,
            "mailchimp_campaign_web_id": None,
            "status": "draft",
            "preview_sent_to": None,
            "preview_sent_at": None,
            "scheduled_for": None,
            "sent_at": None,
            "recipients_count": None,
            "opens_count": None,
            "clicks_count": None,
            "created_at": datetime(2024, 1, 15),
            "updated_at": datetime(2024, 1, 15)
        })

        mock_database.fetchrow.return_value = mock_record
        repo = NewsletterRepository(mock_database)

        result = await repo.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.subject_line == "Weekly Update"

    @pytest.mark.asyncio
    async def test_get_latest(self, mock_database):
        """Test get_latest returns most recent newsletter."""
        from database.repositories.newsletter_repository import NewsletterRepository

        mock_database.fetchrow.return_value = None
        repo = NewsletterRepository(mock_database)

        result = await repo.get_latest()

        assert result is None
        mock_database.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pending_newsletter(self, mock_database):
        """Test get_pending_newsletter returns preview_sent newsletter."""
        from database.repositories.newsletter_repository import NewsletterRepository

        mock_database.fetchrow.return_value = None
        repo = NewsletterRepository(mock_database)

        result = await repo.get_pending_newsletter()

        assert result is None

    @pytest.mark.asyncio
    async def test_update_status(self, mock_database):
        """Test update_status updates newsletter status."""
        from database.repositories.newsletter_repository import NewsletterRepository
        from database.models import NewsletterStatus

        repo = NewsletterRepository(mock_database)

        await repo.update_status(
            newsletter_id=1,
            status=NewsletterStatus.SENT,
            sent_at=datetime(2024, 1, 15, 10, 0)
        )

        mock_database.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_metrics(self, mock_database):
        """Test update_metrics updates newsletter metrics."""
        from database.repositories.newsletter_repository import NewsletterRepository

        repo = NewsletterRepository(mock_database)

        await repo.update_metrics(
            newsletter_id=1,
            recipients_count=100,
            opens_count=50,
            clicks_count=20
        )

        mock_database.execute.assert_called_once()
        call_args = mock_database.execute.call_args[0]
        assert "UPDATE sent_newsletters" in call_args[0]

    @pytest.mark.asyncio
    async def test_link_content(self, mock_database):
        """Test link_content links content to newsletter."""
        from database.repositories.newsletter_repository import NewsletterRepository

        repo = NewsletterRepository(mock_database)

        await repo.link_content(
            newsletter_id=1,
            content_id=5,
            section="news",
            display_order=1
        )

        mock_database.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_newsletters(self, mock_database):
        """Test get_recent_newsletters returns recent newsletters."""
        from database.repositories.newsletter_repository import NewsletterRepository

        mock_database.fetch.return_value = []
        repo = NewsletterRepository(mock_database)

        result = await repo.get_recent_newsletters(limit=10)

        assert result == []
        mock_database.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stats(self, mock_database, mock_record_factory):
        """Test get_stats returns newsletter statistics."""
        from database.repositories.newsletter_repository import NewsletterRepository

        mock_record = mock_record_factory({
            "total": 25,
            "sent": 20,
            "pending_approval": 1,
            "avg_items": 12.5,
            "avg_events": 4.0,
            "total_recipients": 5000,
            "total_opens": 2000,
            "total_clicks": 500
        })
        mock_database.fetchrow.return_value = mock_record
        repo = NewsletterRepository(mock_database)

        result = await repo.get_stats()

        assert result["total"] == 25
        assert result["sent"] == 20
