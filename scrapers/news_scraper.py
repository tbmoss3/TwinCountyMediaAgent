"""
News site scraper using Crawl4AI.
"""
import logging
import re
from typing import List, Optional
from datetime import datetime
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper, ScrapedItem
from config.sources import NewsSource

logger = logging.getLogger(__name__)


class NewsScraper(BaseScraper):
    """Scraper for local news websites using Crawl4AI."""

    def __init__(self, source: NewsSource):
        """
        Initialize news scraper.

        Args:
            source: News source configuration
        """
        super().__init__(source.name, "news")
        self.source = source
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )

    async def scrape(self) -> List[ScrapedItem]:
        """Scrape news articles from the source."""
        items = []

        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                run_config = CrawlerRunConfig(
                    word_count_threshold=50,
                    exclude_external_links=False,
                )

                # First, get the main page to find article links
                self.logger.info(f"Scraping {self.source.display_name}: {self.source.url}")
                result = await crawler.arun(
                    url=self.source.url,
                    config=run_config
                )

                if not result.success:
                    self.logger.error(f"Failed to scrape {self.source.url}: {result.error_message}")
                    return items

                # Extract article URLs from the page
                article_urls = self._extract_article_urls(result.html, result.url)
                self.logger.info(f"Found {len(article_urls)} potential articles")

                # Scrape each article (limit to avoid overwhelming)
                for article_url in article_urls[:15]:
                    try:
                        article_result = await crawler.arun(
                            url=article_url,
                            config=run_config
                        )

                        if article_result.success:
                            item = self._parse_article(article_result, article_url)
                            if item and len(item.content) > 100:
                                items.append(item)
                    except Exception as e:
                        self.logger.warning(f"Error scraping article {article_url}: {e}")

        except Exception as e:
            self.logger.error(f"Error in news scraper for {self.source.name}: {e}")

        self.logger.info(f"Scraped {len(items)} articles from {self.source.display_name}")
        return items

    def _extract_article_urls(self, html: str, base_url: str) -> List[str]:
        """Extract article URLs from page HTML."""
        urls = set()

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Find article links
            for selector in [self.source.article_selector, 'article', '.article', '.story', '.post']:
                articles = soup.select(selector)
                for article in articles:
                    links = article.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        # Filter for article-like URLs
                        if self._is_article_url(href):
                            full_url = urljoin(base_url, href)
                            urls.add(self.normalize_url(full_url, base_url))

            # Also look for common article patterns in all links
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                if self._is_article_url(href):
                    full_url = urljoin(base_url, href)
                    normalized = self.normalize_url(full_url, base_url)
                    # Only include URLs from the same domain
                    if self.source.url in normalized or normalized.startswith('/'):
                        urls.add(normalized)

        except Exception as e:
            self.logger.warning(f"Error extracting article URLs: {e}")

        return list(urls)

    def _is_article_url(self, url: str) -> bool:
        """Check if URL looks like an article."""
        # Skip common non-article patterns
        skip_patterns = [
            '/tag/', '/category/', '/author/', '/page/',
            '/search', '/login', '/subscribe', '/contact',
            '/about', '/privacy', '/terms', '/feed',
            '.pdf', '.jpg', '.png', '.gif',
            'facebook.com', 'twitter.com', 'instagram.com'
        ]

        url_lower = url.lower()
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False

        # Look for article-like patterns
        article_patterns = [
            r'/\d{4}/\d{2}/',  # Date pattern: /2024/01/
            r'/news/',
            r'/article/',
            r'/story/',
            r'/local/',
            r'/sports/',
            r'/business/',
            r'/community/',
            r'-[a-z0-9]{20,}',  # Long slug
        ]

        for pattern in article_patterns:
            if re.search(pattern, url_lower):
                return True

        # If it has a reasonable length path, it might be an article
        if '/' in url and len(url) > 30:
            return True

        return False

    def _parse_article(self, result, url: str) -> Optional[ScrapedItem]:
        """Parse article content from crawl result."""
        try:
            soup = BeautifulSoup(result.html, 'lxml')

            # Extract title
            title = None
            for selector in [self.source.title_selector, 'h1', '.headline', '.title']:
                elem = soup.select_one(selector)
                if elem:
                    title = self.clean_text(elem.get_text())
                    break

            # Use markdown content from Crawl4AI (cleaned)
            content = result.markdown if result.markdown else ""

            # Clean up the content
            content = self.clean_text(content)

            # Skip if too short
            if len(content) < 100:
                return None

            # Extract published date
            published_at = self._extract_date(soup)

            # Extract image
            image_url = self._extract_image(soup)

            # Extract author
            author = self._extract_author(soup)

            return ScrapedItem(
                url=url,
                title=title,
                content=content[:10000],  # Limit content length
                source_name=self.source.name,
                source_type="news",
                source_platform="website",
                image_url=image_url,
                author=author,
                published_at=published_at,
                county=self.source.county.value if self.source.county else None
            )

        except Exception as e:
            self.logger.warning(f"Error parsing article {url}: {e}")
            return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract publication date from article."""
        try:
            # Try common date selectors
            for selector in [self.source.date_selector, 'time', '.date', '.published', '.post-date']:
                elem = soup.select_one(selector)
                if elem:
                    # Try datetime attribute first
                    if elem.get('datetime'):
                        return datetime.fromisoformat(elem['datetime'].replace('Z', '+00:00'))

                    # Try parsing text content
                    date_text = elem.get_text().strip()
                    if date_text:
                        from dateutil import parser
                        try:
                            return parser.parse(date_text)
                        except:
                            pass
        except:
            pass

        return None

    def _extract_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract main image from article."""
        try:
            # Try og:image meta tag first
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                return og_image['content']

            # Try finding main article image
            article = soup.find('article')
            if article:
                img = article.find('img', src=True)
                if img:
                    return img['src']
        except:
            pass

        return None

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author from article."""
        try:
            for selector in ['.author', '.byline', '[rel="author"]', '.writer']:
                elem = soup.select_one(selector)
                if elem:
                    return self.clean_text(elem.get_text())
        except:
            pass

        return None

    async def health_check(self) -> bool:
        """Verify the news source is accessible."""
        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(url=self.source.url)
                return result.success
        except:
            return False
