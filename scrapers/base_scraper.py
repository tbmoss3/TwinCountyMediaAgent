"""
Abstract base class for all scrapers.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import logging


@dataclass
class ScrapedItem:
    """Standardized scraped content item."""
    url: str
    content: str
    source_name: str
    source_type: str
    source_platform: str
    title: Optional[str] = None
    image_url: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    county: Optional[str] = None
    raw_data: Optional[dict] = field(default_factory=dict)

    @property
    def url_hash(self) -> str:
        """Compute SHA256 hash of URL for deduplication."""
        normalized = self.url.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()


class BaseScraper(ABC):
    """Abstract base class for content scrapers."""

    def __init__(self, source_name: str, source_type: str):
        """
        Initialize scraper.

        Args:
            source_name: Unique identifier for the source
            source_type: Type of source ('news', 'social', 'council')
        """
        self.source_name = source_name
        self.source_type = source_type
        self.logger = logging.getLogger(f"scraper.{source_name}")

    @abstractmethod
    async def scrape(self) -> List[ScrapedItem]:
        """
        Execute scraping and return list of items.

        Returns:
            List of scraped items
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if source is accessible.

        Returns:
            True if healthy, False otherwise
        """
        pass

    def normalize_url(self, url: str, base_url: str = "") -> str:
        """
        Normalize URL for deduplication.

        Args:
            url: URL to normalize
            base_url: Base URL to prepend for relative URLs
        """
        url = url.strip()

        # Handle relative URLs
        if url.startswith("/"):
            url = f"{base_url.rstrip('/')}{url}"
        elif not url.startswith(("http://", "https://")):
            url = f"{base_url.rstrip('/')}/{url}"

        # Remove tracking parameters
        if "?" in url:
            base, params = url.split("?", 1)
            # Keep only essential params, remove tracking
            tracking_params = ["utm_", "fbclid", "gclid", "ref", "source"]
            clean_params = []
            for param in params.split("&"):
                if not any(param.startswith(t) for t in tracking_params):
                    clean_params.append(param)
            if clean_params:
                url = f"{base}?{'&'.join(clean_params)}"
            else:
                url = base

        # Remove trailing slash
        url = url.rstrip("/")

        return url

    def compute_url_hash(self, url: str) -> str:
        """Compute SHA256 hash of normalized URL."""
        return hashlib.sha256(url.encode()).hexdigest()

    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""

        # Remove extra whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text
