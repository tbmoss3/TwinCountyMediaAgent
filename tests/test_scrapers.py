"""
Unit tests for scrapers module.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib
import sys

# Mock crawl4ai before any imports that depend on it
sys.modules['crawl4ai'] = MagicMock()
sys.modules['crawl4ai.AsyncWebCrawler'] = MagicMock()
sys.modules['crawl4ai.BrowserConfig'] = MagicMock()
sys.modules['crawl4ai.CrawlerRunConfig'] = MagicMock()


class TestScrapedItem:
    """Test cases for ScrapedItem dataclass."""

    def test_scraped_item_creation(self, sample_scraped_item):
        """Test ScrapedItem creation with all fields."""
        assert sample_scraped_item.url == "https://example.com/article"
        assert sample_scraped_item.source_name == "test_source"
        assert sample_scraped_item.source_type == "news"
        assert sample_scraped_item.title == "Test Article"

    def test_scraped_item_url_hash_property(self):
        """Test ScrapedItem url_hash property computes correct hash."""
        from scrapers.base_scraper import ScrapedItem

        item = ScrapedItem(
            url="https://example.com/test",
            content="Test content",
            source_name="test",
            source_type="news",
            source_platform="website"
        )

        expected_hash = hashlib.sha256("https://example.com/test".encode()).hexdigest()
        assert item.url_hash == expected_hash

    def test_scraped_item_url_hash_normalizes(self):
        """Test url_hash normalizes URL before hashing."""
        from scrapers.base_scraper import ScrapedItem

        item1 = ScrapedItem(
            url="https://example.com/test",
            content="Test",
            source_name="test",
            source_type="news",
            source_platform="website"
        )

        item2 = ScrapedItem(
            url="  HTTPS://EXAMPLE.COM/TEST  ",
            content="Test",
            source_name="test",
            source_type="news",
            source_platform="website"
        )

        assert item1.url_hash == item2.url_hash

    def test_scraped_item_default_values(self):
        """Test ScrapedItem default values for optional fields."""
        from scrapers.base_scraper import ScrapedItem

        item = ScrapedItem(
            url="https://example.com/test",
            content="Test content",
            source_name="test",
            source_type="news",
            source_platform="website"
        )

        assert item.title is None
        assert item.image_url is None
        assert item.author is None
        assert item.published_at is None
        assert item.county is None
        assert item.raw_data == {}


class TestBaseScraper:
    """Test cases for BaseScraper abstract class."""

    def test_normalize_url_absolute_url(self):
        """Test normalize_url with absolute URL."""
        from scrapers.base_scraper import BaseScraper

        # Create a concrete implementation for testing
        class TestScraper(BaseScraper):
            async def scrape(self):
                return []
            async def health_check(self):
                return True

        scraper = TestScraper("test", "news")
        result = scraper.normalize_url("https://example.com/article", "https://base.com")

        assert result == "https://example.com/article"

    def test_normalize_url_relative_path(self):
        """Test normalize_url with relative path."""
        from scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            async def scrape(self):
                return []
            async def health_check(self):
                return True

        scraper = TestScraper("test", "news")
        result = scraper.normalize_url("/article/123", "https://example.com")

        assert result == "https://example.com/article/123"

    def test_normalize_url_removes_tracking_params(self):
        """Test normalize_url removes tracking parameters."""
        from scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            async def scrape(self):
                return []
            async def health_check(self):
                return True

        scraper = TestScraper("test", "news")
        result = scraper.normalize_url(
            "https://example.com/article?utm_source=twitter&utm_medium=social&id=123",
            ""
        )

        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "id=123" in result

    def test_normalize_url_removes_trailing_slash(self):
        """Test normalize_url removes trailing slash."""
        from scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            async def scrape(self):
                return []
            async def health_check(self):
                return True

        scraper = TestScraper("test", "news")
        result = scraper.normalize_url("https://example.com/article/", "")

        assert result == "https://example.com/article"

    def test_normalize_url_fbclid_removal(self):
        """Test normalize_url removes Facebook click ID."""
        from scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            async def scrape(self):
                return []
            async def health_check(self):
                return True

        scraper = TestScraper("test", "news")
        result = scraper.normalize_url(
            "https://example.com/article?fbclid=abc123",
            ""
        )

        assert "fbclid" not in result
        assert result == "https://example.com/article"

    def test_compute_url_hash(self):
        """Test compute_url_hash method."""
        from scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            async def scrape(self):
                return []
            async def health_check(self):
                return True

        scraper = TestScraper("test", "news")
        url = "https://example.com/test"
        expected = hashlib.sha256(url.encode()).hexdigest()

        assert scraper.compute_url_hash(url) == expected

    def test_clean_text_removes_extra_whitespace(self):
        """Test clean_text removes extra whitespace."""
        from scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            async def scrape(self):
                return []
            async def health_check(self):
                return True

        scraper = TestScraper("test", "news")
        result = scraper.clean_text("  This   is   a    test   ")

        assert result == "This is a test"

    def test_clean_text_handles_empty_string(self):
        """Test clean_text handles empty string."""
        from scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            async def scrape(self):
                return []
            async def health_check(self):
                return True

        scraper = TestScraper("test", "news")
        result = scraper.clean_text("")

        assert result == ""

    def test_clean_text_handles_none(self):
        """Test clean_text handles None input."""
        from scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            async def scrape(self):
                return []
            async def health_check(self):
                return True

        scraper = TestScraper("test", "news")
        result = scraper.clean_text(None)

        assert result == ""

    def test_clean_text_handles_newlines(self):
        """Test clean_text handles newlines and tabs."""
        from scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            async def scrape(self):
                return []
            async def health_check(self):
                return True

        scraper = TestScraper("test", "news")
        result = scraper.clean_text("Line1\n\nLine2\t\tLine3")

        assert result == "Line1 Line2 Line3"

    def test_scraper_initialization(self):
        """Test scraper initialization sets attributes."""
        from scrapers.base_scraper import BaseScraper

        class TestScraper(BaseScraper):
            async def scrape(self):
                return []
            async def health_check(self):
                return True

        scraper = TestScraper("my_source", "news")

        assert scraper.source_name == "my_source"
        assert scraper.source_type == "news"
        assert scraper.logger is not None


class TestNewsScraper:
    """Test cases for NewsScraper."""

    def test_news_scraper_initialization(self, sample_news_source):
        """Test NewsScraper initialization."""
        from scrapers.news_scraper import NewsScraper

        scraper = NewsScraper(sample_news_source)

        assert scraper.source_name == "test_news"
        assert scraper.source_type == "news"
        assert scraper.source == sample_news_source

    def test_is_article_url_date_pattern(self, sample_news_source):
        """Test _is_article_url detects date pattern URLs."""
        from scrapers.news_scraper import NewsScraper

        scraper = NewsScraper(sample_news_source)

        assert scraper._is_article_url("/2024/01/15/article-title") is True
        assert scraper._is_article_url("/2024/01/article") is True

    def test_is_article_url_news_pattern(self, sample_news_source):
        """Test _is_article_url detects news pattern URLs."""
        from scrapers.news_scraper import NewsScraper

        scraper = NewsScraper(sample_news_source)

        assert scraper._is_article_url("/news/local-story") is True
        assert scraper._is_article_url("/article/breaking-news") is True
        assert scraper._is_article_url("/story/community-event") is True

    def test_is_article_url_rejects_non_article(self, sample_news_source):
        """Test _is_article_url rejects non-article URLs."""
        from scrapers.news_scraper import NewsScraper

        scraper = NewsScraper(sample_news_source)

        assert scraper._is_article_url("/tag/politics") is False
        assert scraper._is_article_url("/category/sports") is False
        assert scraper._is_article_url("/author/john-doe") is False
        assert scraper._is_article_url("/login") is False
        assert scraper._is_article_url("/subscribe") is False
        assert scraper._is_article_url("facebook.com/page") is False

    def test_is_article_url_rejects_media_files(self, sample_news_source):
        """Test _is_article_url rejects media file URLs."""
        from scrapers.news_scraper import NewsScraper

        scraper = NewsScraper(sample_news_source)

        assert scraper._is_article_url("/images/photo.jpg") is False
        assert scraper._is_article_url("/document.pdf") is False
        assert scraper._is_article_url("/image.png") is False

    @pytest.mark.asyncio
    async def test_scrape_handles_failure(self, sample_news_source):
        """Test scrape handles crawler failure gracefully."""
        from scrapers.news_scraper import NewsScraper

        scraper = NewsScraper(sample_news_source)

        # Mock the crawler to return failure
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Connection refused"

        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock(return_value=mock_result)
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)

        with patch("scrapers.news_scraper.AsyncWebCrawler", return_value=mock_crawler):
            result = await scraper.scrape()

        assert result == []

    def test_extract_article_urls_empty_html(self, sample_news_source):
        """Test _extract_article_urls handles empty HTML."""
        from scrapers.news_scraper import NewsScraper

        scraper = NewsScraper(sample_news_source)

        result = scraper._extract_article_urls("", "https://example.com")

        assert result == []

    def test_extract_article_urls_basic_html(self, sample_news_source):
        """Test _extract_article_urls extracts URLs from HTML."""
        from scrapers.news_scraper import NewsScraper

        scraper = NewsScraper(sample_news_source)

        html = """
        <html>
        <body>
            <article>
                <a href="/news/local-event-announcement">Local Event</a>
            </article>
            <article>
                <a href="/2024/01/15/community-update">Community Update</a>
            </article>
        </body>
        </html>
        """

        result = scraper._extract_article_urls(html, "https://example.com")

        assert len(result) >= 1


class TestCouncilScraper:
    """Test cases for CouncilScraper."""

    def test_council_scraper_initialization(self, sample_council_source):
        """Test CouncilScraper initialization."""
        from scrapers.council_scraper import CouncilScraper

        scraper = CouncilScraper(sample_council_source)

        assert scraper.source_name == "test_council"
        assert scraper.source_type == "council"
        assert scraper.source == sample_council_source

    def test_extract_date_from_text_date_format(self, sample_council_source):
        """Test _extract_date_from_text with various date formats."""
        from scrapers.council_scraper import CouncilScraper

        scraper = CouncilScraper(sample_council_source)

        # Test MM/DD/YYYY format
        result = scraper._extract_date_from_text("Meeting on 01/15/2024")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_extract_date_from_text_written_format(self, sample_council_source):
        """Test _extract_date_from_text with written date."""
        from scrapers.council_scraper import CouncilScraper

        scraper = CouncilScraper(sample_council_source)

        result = scraper._extract_date_from_text("Meeting January 15, 2024")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1

    def test_extract_date_from_text_no_date(self, sample_council_source):
        """Test _extract_date_from_text returns None for no date."""
        from scrapers.council_scraper import CouncilScraper

        scraper = CouncilScraper(sample_council_source)

        result = scraper._extract_date_from_text("Regular Meeting Minutes")
        assert result is None

    def test_extract_date_from_url_yyyy_mm_dd(self, sample_council_source):
        """Test _extract_date_from_url with YYYY-MM-DD format."""
        from scrapers.council_scraper import CouncilScraper

        scraper = CouncilScraper(sample_council_source)

        result = scraper._extract_date_from_url("/minutes/2024-01-15-meeting.pdf")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_extract_date_from_url_yyyymmdd(self, sample_council_source):
        """Test _extract_date_from_url with YYYYMMDD format."""
        from scrapers.council_scraper import CouncilScraper

        scraper = CouncilScraper(sample_council_source)

        result = scraper._extract_date_from_url("/minutes/20240115_agenda.pdf")
        assert result is not None
        assert result.year == 2024

    def test_extract_date_from_url_no_date(self, sample_council_source):
        """Test _extract_date_from_url returns None for no date."""
        from scrapers.council_scraper import CouncilScraper

        scraper = CouncilScraper(sample_council_source)

        result = scraper._extract_date_from_url("/minutes/regular-meeting.pdf")
        assert result is None

    def test_create_meeting_content(self, sample_council_source):
        """Test _create_meeting_content generates content."""
        from scrapers.council_scraper import CouncilScraper

        scraper = CouncilScraper(sample_council_source)

        content = scraper._create_meeting_content(
            title="Council Meeting Minutes",
            date=datetime(2024, 1, 15),
            url="https://example.com/minutes.pdf"
        )

        assert "Council Meeting Minutes" in content
        assert "Test Town Council" in content
        assert "Nash County" in content
        assert "January 15, 2024" in content

    def test_extract_meeting_urls_filters_duplicates(self, sample_council_source):
        """Test _extract_meeting_urls removes duplicate URLs."""
        from scrapers.council_scraper import CouncilScraper

        scraper = CouncilScraper(sample_council_source)

        html = """
        <html>
        <body>
            <a href="/minutes/jan-2024.pdf">January Minutes</a>
            <a href="/minutes/jan-2024.pdf">January Minutes (duplicate)</a>
            <a href="/minutes/feb-2024.pdf">February Minutes</a>
        </body>
        </html>
        """

        result = scraper._extract_meeting_urls(html, "https://example.gov")

        urls = [url for url, _, _ in result]
        assert len(urls) == len(set(urls))  # No duplicates


class TestBrightDataSocialScraper:
    """Test cases for BrightDataSocialScraper."""

    def test_social_scraper_initialization(self, sample_social_source, mock_settings):
        """Test BrightDataSocialScraper initialization."""
        from scrapers.social_scraper import BrightDataSocialScraper

        with patch("scrapers.social_scraper.get_settings", return_value=mock_settings):
            scraper = BrightDataSocialScraper(sample_social_source)

        assert scraper.source_name == "test_restaurant"
        assert scraper.source_type == "social"
        assert scraper.source == sample_social_source

    def test_is_configured_with_api_key(self, sample_social_source, mock_settings):
        """Test is_configured returns True when API key is set."""
        from scrapers.social_scraper import BrightDataSocialScraper

        with patch("scrapers.social_scraper.get_settings", return_value=mock_settings):
            scraper = BrightDataSocialScraper(sample_social_source)

        assert scraper.is_configured() is True

    def test_is_configured_without_api_key(self, sample_social_source):
        """Test is_configured returns False when API key is not set."""
        from scrapers.social_scraper import BrightDataSocialScraper
        from config.settings import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.bright_data_api_key = None

        with patch("scrapers.social_scraper.get_settings", return_value=mock_settings):
            scraper = BrightDataSocialScraper(sample_social_source)

        assert scraper.is_configured() is False

    @pytest.mark.asyncio
    async def test_scrape_returns_empty_when_not_configured(self, sample_social_source):
        """Test scrape returns empty list when not configured."""
        from scrapers.social_scraper import BrightDataSocialScraper
        from config.settings import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.bright_data_api_key = None

        with patch("scrapers.social_scraper.get_settings", return_value=mock_settings):
            scraper = BrightDataSocialScraper(sample_social_source)
            result = await scraper.scrape()

        assert result == []

    def test_parse_post_with_complete_data(self, sample_social_source, mock_settings):
        """Test _parse_post parses complete post data."""
        from scrapers.social_scraper import BrightDataSocialScraper

        with patch("scrapers.social_scraper.get_settings", return_value=mock_settings):
            scraper = BrightDataSocialScraper(sample_social_source)

        post_data = {
            "url": "https://facebook.com/post/123",
            "text": "Check out our special today! Join us for dinner.",
            "date": "2024-01-15T10:30:00",
            "image_url": "https://example.com/image.jpg"
        }

        result = scraper._parse_post(post_data)

        assert result is not None
        assert result.url == "https://facebook.com/post/123"
        assert "special today" in result.content
        assert result.source_platform == "facebook"

    def test_parse_post_skips_short_content(self, sample_social_source, mock_settings):
        """Test _parse_post skips posts with short content."""
        from scrapers.social_scraper import BrightDataSocialScraper

        with patch("scrapers.social_scraper.get_settings", return_value=mock_settings):
            scraper = BrightDataSocialScraper(sample_social_source)

        post_data = {
            "url": "https://facebook.com/post/123",
            "text": "Hi!",  # Too short
        }

        result = scraper._parse_post(post_data)

        assert result is None

    def test_parse_post_generates_url_if_missing(self, sample_social_source, mock_settings):
        """Test _parse_post generates URL if missing."""
        from scrapers.social_scraper import BrightDataSocialScraper

        with patch("scrapers.social_scraper.get_settings", return_value=mock_settings):
            scraper = BrightDataSocialScraper(sample_social_source)

        post_data = {
            "text": "Great event tonight! Come join us for live music and food.",
        }

        result = scraper._parse_post(post_data)

        assert result is not None
        assert "facebook.com/TestRestaurant" in result.url

    def test_parse_post_handles_timestamp_date(self, sample_social_source, mock_settings):
        """Test _parse_post handles Unix timestamp dates."""
        from scrapers.social_scraper import BrightDataSocialScraper

        with patch("scrapers.social_scraper.get_settings", return_value=mock_settings):
            scraper = BrightDataSocialScraper(sample_social_source)

        post_data = {
            "url": "https://facebook.com/post/123",
            "text": "Anniversary celebration! Join us this weekend for specials.",
            "timestamp": 1705315200  # Unix timestamp for 2024-01-15
        }

        result = scraper._parse_post(post_data)

        assert result is not None
        assert result.published_at is not None

    def test_parse_post_handles_image_list(self, sample_social_source, mock_settings):
        """Test _parse_post handles image_url as list."""
        from scrapers.social_scraper import BrightDataSocialScraper

        with patch("scrapers.social_scraper.get_settings", return_value=mock_settings):
            scraper = BrightDataSocialScraper(sample_social_source)

        post_data = {
            "url": "https://facebook.com/post/123",
            "text": "New menu items! Come try our chef's specials.",
            "image_url": ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
        }

        result = scraper._parse_post(post_data)

        assert result is not None
        assert result.image_url == "https://example.com/img1.jpg"

    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_not_configured(self, sample_social_source):
        """Test health_check returns False when not configured."""
        from scrapers.social_scraper import BrightDataSocialScraper
        from config.settings import Settings

        mock_settings = MagicMock(spec=Settings)
        mock_settings.bright_data_api_key = None

        with patch("scrapers.social_scraper.get_settings", return_value=mock_settings):
            scraper = BrightDataSocialScraper(sample_social_source)
            result = await scraper.health_check()

        assert result is False
