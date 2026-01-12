"""
Application configuration management using Pydantic settings.
"""
from functools import lru_cache
from typing import Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database Configuration
    database_url: str = Field(
        ...,
        description="PostgreSQL connection string"
    )
    database_min_pool_size: int = Field(
        default=2,
        description="Minimum database connection pool size"
    )
    database_max_pool_size: int = Field(
        default=10,
        description="Maximum database connection pool size"
    )

    # Anthropic Claude API
    anthropic_api_key: str = Field(..., description="Anthropic API key")
    claude_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Claude model to use"
    )
    claude_max_tokens: int = Field(
        default=4096,
        description="Maximum tokens for Claude responses"
    )

    # Bright Data Configuration
    # Sign up at https://brightdata.com/ and get API key from dashboard
    # Use the Social Media Scraper product for Facebook/Instagram
    bright_data_api_key: Optional[str] = Field(
        default=None,
        description="Bright Data API key for social media scraping"
    )
    bright_data_customer_id: Optional[str] = Field(
        default=None,
        description="Bright Data customer ID"
    )

    # Mailchimp Configuration
    mailchimp_api_key: str = Field(..., description="Mailchimp API key")
    mailchimp_server_prefix: str = Field(
        ...,
        description="Mailchimp server prefix (e.g., us6)"
    )
    mailchimp_list_id: str = Field(
        ...,
        description="Main audience list ID"
    )
    mailchimp_from_name: str = Field(
        default="Twin County Weekly",
        description="Newsletter sender name"
    )
    mailchimp_reply_to: str = Field(
        ...,
        description="Reply-to email address"
    )

    # Manager/Preview Settings
    manager_email: str = Field(
        ...,
        description="Email for draft preview"
    )
    preview_delay_hours: int = Field(
        default=2,
        description="Hours to wait after preview before auto-send"
    )

    # Newsletter Schedule
    newsletter_day: str = Field(
        default="thursday",
        description="Day of week for newsletter"
    )
    newsletter_hour: int = Field(
        default=8,
        description="Hour to generate newsletter (24h format)"
    )
    newsletter_minute: int = Field(
        default=0,
        description="Minute to generate newsletter"
    )

    # Application Settings
    port: int = Field(default=8000, description="Application port")
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Debug mode")

    # Security Settings
    admin_api_key: Optional[str] = Field(
        default=None,
        description="API key for admin endpoints (required in production)"
    )

    # Scraping Settings
    scrape_frequency_hours: int = Field(
        default=6,
        description="Hours between scraping runs"
    )
    content_lookback_days: int = Field(
        default=7,
        description="Days to look back for content"
    )
    max_items_per_source: int = Field(
        default=20,
        description="Maximum items to fetch per source"
    )
    scraper_rate_limit_seconds: float = Field(
        default=2.0,
        description="Seconds to wait between scraping different sources"
    )

    # Resilience Settings
    api_retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for external API calls"
    )
    api_retry_min_wait: float = Field(
        default=2.0,
        description="Minimum wait time between retries (seconds)"
    )
    api_retry_max_wait: float = Field(
        default=10.0,
        description="Maximum wait time between retries (seconds)"
    )
    circuit_breaker_failure_threshold: int = Field(
        default=5,
        description="Number of failures before circuit breaker opens"
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=60,
        description="Seconds before circuit breaker attempts recovery"
    )

    # Feature Flags
    enable_social_scraping: bool = Field(
        default=True,
        description="Enable social media scraping"
    )
    enable_council_scraping: bool = Field(
        default=True,
        description="Enable council minutes scraping"
    )
    auto_send_after_preview: bool = Field(
        default=True,
        description="Auto-send newsletter after preview delay"
    )

    @field_validator("newsletter_day")
    @classmethod
    def validate_newsletter_day(cls, v: str) -> str:
        """Ensure newsletter day is valid."""
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        v_lower = v.lower()
        if v_lower not in valid_days:
            raise ValueError(f"newsletter_day must be one of {valid_days}")
        return v_lower

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    @property
    def social_scraping_enabled(self) -> bool:
        """Check if social scraping is configured and enabled."""
        return self.enable_social_scraping and self.bright_data_api_key is not None

    @property
    def requires_api_auth(self) -> bool:
        """Check if API authentication is required (production) or optional."""
        return self.is_production or self.admin_api_key is not None

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Validate that production has required security settings."""
        if self.is_production and not self.admin_api_key:
            raise ValueError("admin_api_key is required in production environment")
        return self


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache for efficient singleton pattern that's also testable.
    """
    return Settings()


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)."""
    get_settings.cache_clear()
    return get_settings()
