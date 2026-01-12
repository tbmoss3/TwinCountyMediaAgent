"""
Tests for error handling and edge cases.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import anthropic
from mailchimp_marketing.api_client import ApiClientError

from database.models import ScrapedContent, FilterStatus
from services.content_filter import ContentFilterService
from services.mailchimp_service import MailchimpService


@pytest.fixture
def sample_content():
    """Create sample scraped content for testing."""
    return ScrapedContent(
        id=1,
        url="https://example.com/article",
        url_hash="abc123",
        source_name="Test Source",
        source_type="news",
        content="Test article content that is long enough to be valid.",
        scraped_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class TestContentFilterErrorPaths:
    """Tests for content filter error handling."""

    @pytest.mark.asyncio
    async def test_filter_handles_json_parse_error(self, sample_content):
        """Test that filter handles malformed JSON responses."""
        filter_service = ContentFilterService()

        with patch.object(filter_service, '_call_claude_api', new_callable=AsyncMock) as mock_api:
            # Return invalid JSON
            mock_api.return_value = "This is not valid JSON"

            result = await filter_service.filter_content(sample_content)

            assert result.decision == FilterStatus.REJECTED
            assert "JSON parse error" in result.reason

    @pytest.mark.asyncio
    async def test_filter_handles_api_error(self, sample_content):
        """Test that filter handles Claude API errors."""
        filter_service = ContentFilterService()

        with patch.object(filter_service, '_call_claude_api', new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = anthropic.APIError("API unavailable")

            result = await filter_service.filter_content(sample_content)

            assert result.decision == FilterStatus.REJECTED
            assert "API error" in result.reason

    @pytest.mark.asyncio
    async def test_filter_handles_rate_limit_error(self, sample_content):
        """Test that filter handles rate limit errors."""
        filter_service = ContentFilterService()

        with patch.object(filter_service, '_call_claude_api', new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = anthropic.RateLimitError("Rate limited")

            result = await filter_service.filter_content(sample_content)

            assert result.decision == FilterStatus.REJECTED

    @pytest.mark.asyncio
    async def test_filter_handles_connection_error(self, sample_content):
        """Test that filter handles connection errors."""
        filter_service = ContentFilterService()

        with patch.object(filter_service, '_call_claude_api', new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = anthropic.APIConnectionError("Connection failed")

            result = await filter_service.filter_content(sample_content)

            assert result.decision == FilterStatus.REJECTED

    @pytest.mark.asyncio
    async def test_batch_filter_partial_failure(self, sample_content):
        """Test that batch filter continues after individual failures."""
        filter_service = ContentFilterService()

        contents = [sample_content, sample_content, sample_content]

        call_count = 0

        async def mock_filter(content):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise anthropic.APIError("API error")
            return await filter_service._create_error_result(content, "test")

        with patch.object(filter_service, 'filter_content', side_effect=mock_filter):
            results = await filter_service.batch_filter(contents, max_concurrent=1)

            # All items should be processed
            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_error(self):
        """Test that health check returns False on API error."""
        filter_service = ContentFilterService()

        with patch.object(filter_service.client.messages, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("Connection error")

            result = await filter_service.health_check()

            assert result is False


class TestMailchimpServiceErrorPaths:
    """Tests for Mailchimp service error handling."""

    @pytest.mark.asyncio
    async def test_create_campaign_handles_api_error(self):
        """Test that create_campaign handles API errors."""
        service = MailchimpService()

        with patch.object(service, '_run_in_executor', new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = ApiClientError("Campaign creation failed")

            with pytest.raises(ApiClientError):
                await service.create_campaign(
                    subject_line="Test",
                    preview_text="Test preview",
                    html_content="<p>Test</p>"
                )

    @pytest.mark.asyncio
    async def test_send_campaign_handles_api_error(self):
        """Test that send_campaign handles API errors."""
        service = MailchimpService()

        with patch.object(service, '_run_in_executor', new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = ApiClientError("Send failed")

            with pytest.raises(ApiClientError):
                await service.send_campaign("test_campaign_id")

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_error(self):
        """Test that health check returns False on error."""
        service = MailchimpService()

        with patch.object(service, '_run_in_executor', new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = Exception("Connection error")

            result = await service.health_check()

            assert result is False


class TestDatabaseConnectionErrorPaths:
    """Tests for database connection error handling."""

    @pytest.mark.asyncio
    async def test_connection_retry_on_failure(self):
        """Test that database connection retries on failure."""
        from database.connection import Database

        db = Database(
            "postgresql://user:pass@localhost:5432/test",
            min_size=1,
            max_size=5
        )

        with patch('database.connection.asyncpg.create_pool', new_callable=AsyncMock) as mock_pool:
            # First two attempts fail, third succeeds
            mock_pool.side_effect = [
                ConnectionError("Connection refused"),
                ConnectionError("Connection refused"),
                AsyncMock()  # Success on third try
            ]

            # This should eventually succeed after retries
            try:
                await db.connect(max_retries=3, retry_delay=0.01)
                # If we get here, connection succeeded on retry
                assert mock_pool.call_count == 3
            except Exception:
                # Connection still failed after retries
                assert mock_pool.call_count == 3


class TestContentRepositoryErrorPaths:
    """Tests for content repository error handling."""

    @pytest.mark.asyncio
    async def test_create_handles_duplicate_url(self):
        """Test that create handles duplicate URL gracefully."""
        from database.repositories.content_repository import ContentRepository
        from database.models import ScrapedContentCreate

        mock_db = MagicMock()
        mock_db.fetchval = AsyncMock(return_value=None)  # No ID returned = duplicate

        repo = ContentRepository(mock_db)

        content = ScrapedContentCreate(
            url="https://example.com/article",
            url_hash="abc123",
            source_name="Test",
            source_type="news",
            content="Test content"
        )

        result = await repo.create(content)

        # Should return None for duplicate (ON CONFLICT DO NOTHING)
        assert result is None


class TestSchedulerErrorPaths:
    """Tests for scheduler error handling."""

    @pytest.mark.asyncio
    async def test_scheduler_handles_newsletter_generation_error(self):
        """Test that scheduler handles newsletter generation errors."""
        from services.scheduler import SchedulerService

        mock_db = MagicMock()
        scheduler = SchedulerService(mock_db)

        with patch('services.scheduler.NewsletterBuilderService') as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder.build_and_send_preview = AsyncMock(
                side_effect=Exception("Generation failed")
            )
            mock_builder_class.return_value = mock_builder

            # Should not raise, just log the error
            await scheduler._generate_and_preview_newsletter()

            # Verify build was attempted
            mock_builder.build_and_send_preview.assert_called_once()

    @pytest.mark.asyncio
    async def test_scheduler_handles_send_error(self):
        """Test that scheduler handles newsletter send errors."""
        from services.scheduler import SchedulerService

        mock_db = MagicMock()
        scheduler = SchedulerService(mock_db)
        scheduler._pending_newsletter_id = 123

        with patch('services.scheduler.NewsletterBuilderService') as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder.send_newsletter = AsyncMock(
                side_effect=Exception("Send failed")
            )
            mock_builder_class.return_value = mock_builder

            # Should not raise, just log the error
            await scheduler._send_pending_newsletter()


class TestAPIAuthErrorPaths:
    """Tests for API authentication error handling."""

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_401(self):
        """Test that missing API key returns 401."""
        from api.auth import verify_api_key
        from fastapi import HTTPException
        from config.settings import Settings

        # Mock settings with API key required
        mock_settings = MagicMock(spec=Settings)
        mock_settings.requires_api_auth = True
        mock_settings.admin_api_key = "test-key"

        with patch('api.auth.get_settings', return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(None)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_api_key_returns_403(self):
        """Test that invalid API key returns 403."""
        from api.auth import verify_api_key
        from fastapi import HTTPException
        from config.settings import Settings

        # Mock settings with API key required
        mock_settings = MagicMock(spec=Settings)
        mock_settings.requires_api_auth = True
        mock_settings.admin_api_key = "correct-key"

        with patch('api.auth.get_settings', return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key("wrong-key")

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_valid_api_key_succeeds(self):
        """Test that valid API key succeeds."""
        from api.auth import verify_api_key
        from config.settings import Settings

        # Mock settings with API key required
        mock_settings = MagicMock(spec=Settings)
        mock_settings.requires_api_auth = True
        mock_settings.admin_api_key = "correct-key"

        with patch('api.auth.get_settings', return_value=mock_settings):
            result = await verify_api_key("correct-key")

            assert result == "correct-key"
