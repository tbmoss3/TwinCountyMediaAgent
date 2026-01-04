"""
Government council/meeting minutes scraper using Crawl4AI.
"""
import logging
import re
from typing import List, Optional
from datetime import datetime
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from bs4 import BeautifulSoup

from scrapers.base_scraper import BaseScraper, ScrapedItem
from config.sources import CouncilSource

logger = logging.getLogger(__name__)


class CouncilScraper(BaseScraper):
    """Scraper for government council meetings and minutes."""

    def __init__(self, source: CouncilSource):
        """
        Initialize council scraper.

        Args:
            source: Council source configuration
        """
        super().__init__(source.name, "council")
        self.source = source
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )

    async def scrape(self) -> List[ScrapedItem]:
        """Scrape meeting minutes and agendas from the source."""
        items = []

        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                run_config = CrawlerRunConfig(
                    word_count_threshold=20,
                    exclude_external_links=False,
                )

                self.logger.info(f"Scraping {self.source.display_name}: {self.source.url}")
                result = await crawler.arun(
                    url=self.source.url,
                    config=run_config
                )

                if not result.success:
                    self.logger.error(f"Failed to scrape {self.source.url}: {result.error_message}")
                    return items

                # Extract meeting/minutes links
                meeting_urls = self._extract_meeting_urls(result.html, result.url)
                self.logger.info(f"Found {len(meeting_urls)} meeting documents")

                # Create items for each meeting document
                for url, title, date in meeting_urls[:20]:  # Limit to 20
                    item = ScrapedItem(
                        url=url,
                        title=title,
                        content=self._create_meeting_content(title, date, url),
                        source_name=self.source.name,
                        source_type="council",
                        source_platform="website",
                        published_at=date,
                        county=self.source.county.value
                    )
                    items.append(item)

        except Exception as e:
            self.logger.error(f"Error in council scraper for {self.source.name}: {e}")

        self.logger.info(f"Scraped {len(items)} meeting items from {self.source.display_name}")
        return items

    def _extract_meeting_urls(self, html: str, base_url: str) -> List[tuple]:
        """
        Extract meeting document URLs from page HTML.

        Returns:
            List of tuples: (url, title, date)
        """
        meetings = []

        try:
            soup = BeautifulSoup(html, 'lxml')

            # Find links to minutes, agendas, and meeting documents
            patterns = [
                (r'minute', 'Minutes'),
                (r'agenda', 'Agenda'),
                (r'meeting', 'Meeting'),
                (r'packet', 'Packet'),
            ]

            all_links = soup.find_all('a', href=True)

            for link in all_links:
                href = link['href']
                text = self.clean_text(link.get_text())

                # Check if it's a meeting-related document
                href_lower = href.lower()
                text_lower = text.lower()

                is_meeting_doc = False
                doc_type = "Meeting"

                for pattern, dtype in patterns:
                    if pattern in href_lower or pattern in text_lower:
                        is_meeting_doc = True
                        doc_type = dtype
                        break

                if is_meeting_doc:
                    full_url = urljoin(base_url, href)
                    normalized = self.normalize_url(full_url, base_url)

                    # Skip non-document links
                    if any(skip in normalized.lower() for skip in ['facebook', 'twitter', 'mailto:']):
                        continue

                    # Try to extract date from text or URL
                    date = self._extract_date_from_text(text) or self._extract_date_from_url(href)

                    # Create title
                    if text and len(text) > 5:
                        title = text
                    else:
                        title = f"{self.source.display_name} - {doc_type}"
                        if date:
                            title += f" ({date.strftime('%B %d, %Y')})"

                    meetings.append((normalized, title, date))

        except Exception as e:
            self.logger.warning(f"Error extracting meeting URLs: {e}")

        # Remove duplicates while preserving order
        seen = set()
        unique_meetings = []
        for url, title, date in meetings:
            if url not in seen:
                seen.add(url)
                unique_meetings.append((url, title, date))

        return unique_meetings

    def _extract_date_from_text(self, text: str) -> Optional[datetime]:
        """Extract date from text."""
        if not text:
            return None

        try:
            from dateutil import parser

            # Common date patterns in meeting minutes
            date_patterns = [
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\w+ \d{1,2},? \d{4})',
                r'(\d{1,2} \w+ \d{4})',
            ]

            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        return parser.parse(match.group(1))
                    except:
                        continue
        except:
            pass

        return None

    def _extract_date_from_url(self, url: str) -> Optional[datetime]:
        """Extract date from URL path."""
        try:
            # Look for date patterns in URL
            patterns = [
                r'(\d{4})[/-](\d{2})[/-](\d{2})',  # YYYY-MM-DD
                r'(\d{2})[/-](\d{2})[/-](\d{4})',  # MM-DD-YYYY
                r'(\d{4})(\d{2})(\d{2})',          # YYYYMMDD
            ]

            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    groups = match.groups()
                    if len(groups[0]) == 4:
                        # YYYY-MM-DD format
                        return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                    else:
                        # MM-DD-YYYY format
                        return datetime(int(groups[2]), int(groups[0]), int(groups[1]))
        except:
            pass

        return None

    def _create_meeting_content(self, title: str, date: Optional[datetime], url: str) -> str:
        """Create content description for meeting document."""
        content_parts = [
            f"Government meeting document: {title}",
            f"Source: {self.source.display_name}",
            f"County: {self.source.county.value.title()} County",
        ]

        if date:
            content_parts.append(f"Meeting Date: {date.strftime('%B %d, %Y')}")

        content_parts.append(f"Document URL: {url}")
        content_parts.append(
            "This is a public government meeting document. "
            "View the full document for meeting details, agenda items, and minutes."
        )

        return "\n".join(content_parts)

    async def health_check(self) -> bool:
        """Verify the council source is accessible."""
        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(url=self.source.url)
                return result.success
        except:
            return False
