"""
Unit tests for config module.
"""
import pytest
import os
import logging
from unittest.mock import patch, MagicMock


class TestSettings:
    """Test cases for Settings configuration."""

    def test_settings_loads_from_environment(self, mock_settings):
        """Test that settings load correctly from environment variables."""
        assert mock_settings.database_url == "postgresql://test:test@localhost/testdb"
        assert mock_settings.anthropic_api_key == "sk-ant-test-key"
        assert mock_settings.mailchimp_api_key == "test-mc-key-us1"
        assert mock_settings.environment == "testing"

    def test_settings_default_values(self, mock_settings):
        """Test default values for optional settings."""
        assert mock_settings.database_min_pool_size == 2
        assert mock_settings.database_max_pool_size == 10
        assert mock_settings.claude_model == "claude-sonnet-4-5-20250929"
        assert mock_settings.claude_max_tokens == 4096
        assert mock_settings.port == 8000
        assert mock_settings.scrape_frequency_hours == 6
        assert mock_settings.content_lookback_days == 7
        assert mock_settings.preview_delay_hours == 2
        assert mock_settings.newsletter_day == "thursday"
        assert mock_settings.newsletter_hour == 8
        assert mock_settings.newsletter_minute == 0

    def test_settings_feature_flags(self, mock_settings):
        """Test feature flag defaults."""
        assert mock_settings.enable_social_scraping is True
        assert mock_settings.enable_council_scraping is True
        assert mock_settings.auto_send_after_preview is True

    def test_settings_is_production_property(self, mock_settings):
        """Test is_production property."""
        assert mock_settings.is_production is False

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            from config.settings import Settings
            prod_settings = Settings()
            assert prod_settings.is_production is True

    def test_settings_is_development_property(self, mock_settings):
        """Test is_development property."""
        # Testing environment is not development
        assert mock_settings.is_development is False

        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "ANTHROPIC_API_KEY": "test-key",
            "MAILCHIMP_API_KEY": "test-mc-key",
            "MAILCHIMP_SERVER_PREFIX": "us1",
            "MAILCHIMP_LIST_ID": "test-list",
            "MAILCHIMP_REPLY_TO": "test@test.com",
            "MANAGER_EMAIL": "mgr@test.com",
            "ENVIRONMENT": "development"
        }):
            from config.settings import Settings
            dev_settings = Settings()
            assert dev_settings.is_development is True

    def test_settings_social_scraping_enabled_property(self, mock_settings):
        """Test social_scraping_enabled property."""
        # Should be True when both enable_social_scraping and bright_data_api_key are set
        assert mock_settings.social_scraping_enabled is True

    def test_settings_social_scraping_disabled_without_api_key(self):
        """Test social scraping is disabled without API key."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "ANTHROPIC_API_KEY": "test-key",
            "MAILCHIMP_API_KEY": "test-mc-key",
            "MAILCHIMP_SERVER_PREFIX": "us1",
            "MAILCHIMP_LIST_ID": "test-list",
            "MAILCHIMP_REPLY_TO": "test@test.com",
            "MANAGER_EMAIL": "mgr@test.com",
        }, clear=False):
            # Remove bright data key if present
            os.environ.pop("BRIGHT_DATA_API_KEY", None)
            from config.settings import Settings
            settings = Settings()
            assert settings.social_scraping_enabled is False

    def test_newsletter_day_validation_valid(self):
        """Test newsletter_day validator accepts valid days."""
        from config.settings import Settings

        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for day in valid_days:
            with patch.dict(os.environ, {
                "DATABASE_URL": "postgresql://test:test@localhost/test",
                "ANTHROPIC_API_KEY": "test-key",
                "MAILCHIMP_API_KEY": "test-mc-key",
                "MAILCHIMP_SERVER_PREFIX": "us1",
                "MAILCHIMP_LIST_ID": "test-list",
                "MAILCHIMP_REPLY_TO": "test@test.com",
                "MANAGER_EMAIL": "mgr@test.com",
                "NEWSLETTER_DAY": day
            }):
                settings = Settings()
                assert settings.newsletter_day == day.lower()

    def test_newsletter_day_validation_case_insensitive(self):
        """Test newsletter_day validator is case insensitive."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "ANTHROPIC_API_KEY": "test-key",
            "MAILCHIMP_API_KEY": "test-mc-key",
            "MAILCHIMP_SERVER_PREFIX": "us1",
            "MAILCHIMP_LIST_ID": "test-list",
            "MAILCHIMP_REPLY_TO": "test@test.com",
            "MANAGER_EMAIL": "mgr@test.com",
            "NEWSLETTER_DAY": "THURSDAY"
        }):
            from config.settings import Settings
            settings = Settings()
            assert settings.newsletter_day == "thursday"

    def test_newsletter_day_validation_invalid(self):
        """Test newsletter_day validator rejects invalid days."""
        from pydantic import ValidationError
        from config.settings import Settings

        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "ANTHROPIC_API_KEY": "test-key",
            "MAILCHIMP_API_KEY": "test-mc-key",
            "MAILCHIMP_SERVER_PREFIX": "us1",
            "MAILCHIMP_LIST_ID": "test-list",
            "MAILCHIMP_REPLY_TO": "test@test.com",
            "MANAGER_EMAIL": "mgr@test.com",
            "NEWSLETTER_DAY": "invalidday"
        }):
            with pytest.raises(ValidationError):
                Settings()

    def test_log_level_validation_valid(self):
        """Test log_level validator accepts valid levels."""
        from config.settings import Settings

        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            with patch.dict(os.environ, {
                "DATABASE_URL": "postgresql://test:test@localhost/test",
                "ANTHROPIC_API_KEY": "test-key",
                "MAILCHIMP_API_KEY": "test-mc-key",
                "MAILCHIMP_SERVER_PREFIX": "us1",
                "MAILCHIMP_LIST_ID": "test-list",
                "MAILCHIMP_REPLY_TO": "test@test.com",
                "MANAGER_EMAIL": "mgr@test.com",
                "LOG_LEVEL": level
            }):
                settings = Settings()
                assert settings.log_level == level.upper()

    def test_log_level_validation_case_insensitive(self):
        """Test log_level validator is case insensitive."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "ANTHROPIC_API_KEY": "test-key",
            "MAILCHIMP_API_KEY": "test-mc-key",
            "MAILCHIMP_SERVER_PREFIX": "us1",
            "MAILCHIMP_LIST_ID": "test-list",
            "MAILCHIMP_REPLY_TO": "test@test.com",
            "MANAGER_EMAIL": "mgr@test.com",
            "LOG_LEVEL": "debug"
        }):
            from config.settings import Settings
            settings = Settings()
            assert settings.log_level == "DEBUG"

    def test_log_level_validation_invalid(self):
        """Test log_level validator rejects invalid levels."""
        from pydantic import ValidationError
        from config.settings import Settings

        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://test:test@localhost/test",
            "ANTHROPIC_API_KEY": "test-key",
            "MAILCHIMP_API_KEY": "test-mc-key",
            "MAILCHIMP_SERVER_PREFIX": "us1",
            "MAILCHIMP_LIST_ID": "test-list",
            "MAILCHIMP_REPLY_TO": "test@test.com",
            "MANAGER_EMAIL": "mgr@test.com",
            "LOG_LEVEL": "INVALID"
        }):
            with pytest.raises(ValidationError):
                Settings()


class TestSources:
    """Test cases for source configurations."""

    def test_source_type_enum_values(self):
        """Test SourceType enum values."""
        from config.sources import SourceType

        assert SourceType.NEWS.value == "news"
        assert SourceType.SOCIAL.value == "social"
        assert SourceType.COUNCIL.value == "council"

    def test_county_enum_values(self):
        """Test County enum values."""
        from config.sources import County

        assert County.NASH.value == "nash"
        assert County.EDGECOMBE.value == "edgecombe"
        assert County.WILSON.value == "wilson"

    def test_news_source_dataclass(self, sample_news_source):
        """Test NewsSource dataclass creation."""
        assert sample_news_source.name == "test_news"
        assert sample_news_source.display_name == "Test News Source"
        assert sample_news_source.url == "https://testnews.com"
        assert sample_news_source.is_active is True

    def test_council_source_dataclass(self, sample_council_source):
        """Test CouncilSource dataclass creation."""
        assert sample_council_source.name == "test_council"
        assert sample_council_source.display_name == "Test Town Council"
        assert sample_council_source.url == "https://testtown.gov/council"

    def test_social_source_dataclass(self, sample_social_source):
        """Test SocialSource dataclass creation."""
        assert sample_social_source.name == "test_restaurant"
        assert sample_social_source.platform == "facebook"
        assert sample_social_source.account_id == "TestRestaurant"

    def test_get_active_news_sources(self):
        """Test get_active_news_sources function."""
        from config.sources import get_active_news_sources, NEWS_SOURCES

        active_sources = get_active_news_sources()

        # Should return only active sources
        for source in active_sources:
            assert source.is_active is True

        # Count should match active sources in NEWS_SOURCES
        expected_count = sum(1 for s in NEWS_SOURCES if s.is_active)
        assert len(active_sources) == expected_count

    def test_get_active_council_sources(self):
        """Test get_active_council_sources function."""
        from config.sources import get_active_council_sources, COUNCIL_SOURCES

        active_sources = get_active_council_sources()

        for source in active_sources:
            assert source.is_active is True

        expected_count = sum(1 for s in COUNCIL_SOURCES if s.is_active)
        assert len(active_sources) == expected_count

    def test_get_active_social_sources(self):
        """Test get_active_social_sources function."""
        from config.sources import get_active_social_sources, ALL_SOCIAL_SOURCES

        active_sources = get_active_social_sources()

        for source in active_sources:
            assert source.is_active is True

        expected_count = sum(1 for s in ALL_SOCIAL_SOURCES if s.is_active)
        assert len(active_sources) == expected_count

    def test_get_sources_by_county_nash(self):
        """Test get_sources_by_county for Nash county."""
        from config.sources import get_sources_by_county, County

        sources = get_sources_by_county(County.NASH)

        assert "news" in sources
        assert "council" in sources
        assert "social" in sources

        # All returned sources should be for Nash county
        for news_source in sources["news"]:
            assert news_source.county == County.NASH

        for council_source in sources["council"]:
            assert council_source.county == County.NASH

        for social_source in sources["social"]:
            assert social_source.county == County.NASH

    def test_get_sources_by_county_edgecombe(self):
        """Test get_sources_by_county for Edgecombe county."""
        from config.sources import get_sources_by_county, County

        sources = get_sources_by_county(County.EDGECOMBE)

        for council_source in sources["council"]:
            assert council_source.county == County.EDGECOMBE

    def test_news_sources_list_populated(self):
        """Test that NEWS_SOURCES list is populated."""
        from config.sources import NEWS_SOURCES

        assert len(NEWS_SOURCES) > 0
        # Check first source has required fields
        first_source = NEWS_SOURCES[0]
        assert first_source.name is not None
        assert first_source.url is not None

    def test_council_sources_list_populated(self):
        """Test that COUNCIL_SOURCES list is populated."""
        from config.sources import COUNCIL_SOURCES

        assert len(COUNCIL_SOURCES) > 0

    def test_social_sources_combined_list(self):
        """Test that ALL_SOCIAL_SOURCES combines restaurant and community sources."""
        from config.sources import (
            ALL_SOCIAL_SOURCES,
            RESTAURANT_SOCIAL_SOURCES,
            COMMUNITY_SOCIAL_SOURCES
        )

        expected_count = len(RESTAURANT_SOCIAL_SOURCES) + len(COMMUNITY_SOCIAL_SOURCES)
        assert len(ALL_SOCIAL_SOURCES) == expected_count


class TestLoggingConfig:
    """Test cases for logging configuration."""

    def test_sensitive_data_filter_masks_api_keys(self):
        """Test SensitiveDataFilter masks API keys."""
        from config.logging_config import SensitiveDataFilter

        filter_instance = SensitiveDataFilter()
        record = MagicMock()
        record.msg = "API key is sk-ant-abc123def456"

        filter_instance.filter(record)

        assert "sk-ant-abc123def456" not in record.msg
        assert "sk-ant-***MASKED***" in record.msg

    def test_sensitive_data_filter_masks_passwords(self):
        """Test SensitiveDataFilter masks passwords."""
        from config.logging_config import SensitiveDataFilter

        filter_instance = SensitiveDataFilter()
        record = MagicMock()
        record.msg = "password=secretpassword123"

        filter_instance.filter(record)

        assert "secretpassword123" not in record.msg
        assert "***MASKED***" in record.msg

    def test_sensitive_data_filter_masks_postgres_url(self):
        """Test SensitiveDataFilter masks PostgreSQL passwords in URLs."""
        from config.logging_config import SensitiveDataFilter

        filter_instance = SensitiveDataFilter()
        record = MagicMock()
        record.msg = "Connecting to postgresql://user:mysecretpwd@localhost/db"

        filter_instance.filter(record)

        assert "mysecretpwd" not in record.msg
        assert "***MASKED***" in record.msg

    def test_sensitive_data_filter_masks_bearer_tokens(self):
        """Test SensitiveDataFilter masks Bearer tokens."""
        from config.logging_config import SensitiveDataFilter

        filter_instance = SensitiveDataFilter()
        record = MagicMock()
        record.msg = "Authorization: Bearer abc123xyz789"

        filter_instance.filter(record)

        assert "abc123xyz789" not in record.msg
        assert "***MASKED***" in record.msg

    def test_sensitive_data_filter_returns_true(self):
        """Test SensitiveDataFilter always returns True to allow log entry."""
        from config.logging_config import SensitiveDataFilter

        filter_instance = SensitiveDataFilter()
        record = MagicMock()
        record.msg = "Normal log message"

        result = filter_instance.filter(record)

        assert result is True

    def test_sensitive_data_filter_handles_no_msg(self):
        """Test SensitiveDataFilter handles records without msg."""
        from config.logging_config import SensitiveDataFilter

        filter_instance = SensitiveDataFilter()
        record = MagicMock()
        record.msg = None

        # Should not raise exception
        result = filter_instance.filter(record)
        assert result is True

    def test_setup_logging_creates_handlers(self):
        """Test setup_logging creates proper handlers."""
        from config.logging_config import setup_logging

        # Get root logger state before
        root_logger = logging.getLogger()
        initial_handlers = len(root_logger.handlers)

        setup_logging("DEBUG")

        # Should have at least one handler
        assert len(root_logger.handlers) >= 1

        # Clean up
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_setup_logging_sets_third_party_log_levels(self):
        """Test setup_logging reduces noise from third-party libraries."""
        from config.logging_config import setup_logging

        setup_logging("INFO")

        # Third-party loggers should be set to WARNING
        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("httpcore").level == logging.WARNING
        assert logging.getLogger("asyncio").level == logging.WARNING
        assert logging.getLogger("playwright").level == logging.WARNING

        # Clean up
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
