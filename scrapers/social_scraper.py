"""
Social media scraper using Bright Data API.

Bright Data Setup Instructions:
1. Sign up at https://brightdata.com/
2. Go to Dashboard > Products > Social Media Scraper
3. Enable Facebook and Instagram scrapers
4. Get your API key from: Dashboard > Account Settings > API Tokens
5. Set BRIGHT_DATA_API_KEY and BRIGHT_DATA_CUSTOMER_ID in environment

Alternative: If Bright Data is not configured, this scraper will be skipped
and you can add social content manually through the admin API.
"""
import logging
import httpx
import asyncio
from typing import List, Optional
from datetime import datetime

from scrapers.base_scraper import BaseScraper, ScrapedItem
from config.sources import SocialSource
from config.settings import get_settings

logger = logging.getLogger(__name__)


class BrightDataSocialScraper(BaseScraper):
    """Scraper for social media using Bright Data Social Media Scraper API."""

    # Bright Data dataset IDs (these may need updating based on your Bright Data account)
    FACEBOOK_POSTS_DATASET = "gd_lfqw89hkdh82gx"
    INSTAGRAM_POSTS_DATASET = "gd_lk5ns7kz21pck8"

    BASE_URL = "https://api.brightdata.com/datasets/v3"

    def __init__(self, source: SocialSource):
        """
        Initialize social media scraper.

        Args:
            source: Social media source configuration
        """
        super().__init__(source.name, "social")
        self.source = source
        self.settings = get_settings()

        if self.settings.bright_data_api_key:
            self.headers = {
                "Authorization": f"Bearer {self.settings.bright_data_api_key}",
                "Content-Type": "application/json"
            }
        else:
            self.headers = {}

    def is_configured(self) -> bool:
        """Check if Bright Data is configured."""
        return bool(self.settings.bright_data_api_key)

    async def scrape(self) -> List[ScrapedItem]:
        """Fetch posts from social media account via Bright Data."""
        items = []

        if not self.is_configured():
            self.logger.warning(
                f"Bright Data not configured. Skipping {self.source.display_name}. "
                "Set BRIGHT_DATA_API_KEY to enable social media scraping."
            )
            return items

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Determine endpoint and payload based on platform
                if self.source.platform == "facebook":
                    payload = {
                        "dataset_id": self.FACEBOOK_POSTS_DATASET,
                        "include_errors": False,
                        "snapshot_id": None,
                        "format": "json",
                        "uncompressed_webhook": True,
                        "filter": f"page_id:{self.source.account_id}",
                        "limit_per_input": self.settings.max_items_per_source
                    }
                elif self.source.platform == "instagram":
                    payload = {
                        "dataset_id": self.INSTAGRAM_POSTS_DATASET,
                        "include_errors": False,
                        "snapshot_id": None,
                        "format": "json",
                        "uncompressed_webhook": True,
                        "filter": f"username:{self.source.account_id}",
                        "limit_per_input": self.settings.max_items_per_source
                    }
                else:
                    self.logger.warning(f"Unknown platform: {self.source.platform}")
                    return items

                self.logger.info(f"Triggering Bright Data scrape for {self.source.display_name}")

                # Trigger the scrape
                response = await client.post(
                    f"{self.BASE_URL}/trigger",
                    headers=self.headers,
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    snapshot_id = result.get("snapshot_id")

                    if snapshot_id:
                        # Wait for results
                        data = await self._wait_for_results(client, snapshot_id)

                        for post in data:
                            item = self._parse_post(post)
                            if item:
                                items.append(item)
                else:
                    self.logger.error(
                        f"Bright Data API error ({response.status_code}): {response.text}"
                    )

        except httpx.TimeoutException:
            self.logger.error(f"Timeout scraping {self.source.display_name}")
        except Exception as e:
            self.logger.error(f"Error in social scraper for {self.source.name}: {e}")

        self.logger.info(f"Scraped {len(items)} posts from {self.source.display_name}")
        return items

    async def _wait_for_results(
        self,
        client: httpx.AsyncClient,
        snapshot_id: str,
        max_wait: int = 300
    ) -> List[dict]:
        """
        Poll Bright Data API until results are ready.

        Args:
            client: HTTP client
            snapshot_id: Bright Data snapshot ID
            max_wait: Maximum wait time in seconds
        """
        status_url = f"{self.BASE_URL}/snapshot/{snapshot_id}"

        for _ in range(max_wait // 5):
            response = await client.get(status_url, headers=self.headers)

            if response.status_code != 200:
                raise Exception(f"Error checking status: {response.text}")

            result = response.json()
            status = result.get("status")

            if status == "ready":
                # Fetch the actual data
                data_url = f"{self.BASE_URL}/snapshot/{snapshot_id}/data"
                data_response = await client.get(data_url, headers=self.headers)

                if data_response.status_code == 200:
                    return data_response.json()
                else:
                    raise Exception(f"Error fetching data: {data_response.text}")

            elif status == "failed":
                raise Exception(f"Bright Data scrape failed: {result.get('error')}")

            self.logger.debug(f"Waiting for Bright Data results... Status: {status}")
            await asyncio.sleep(5)

        raise TimeoutError("Bright Data scrape timed out")

    def _parse_post(self, post: dict) -> Optional[ScrapedItem]:
        """Parse a social media post into ScrapedItem."""
        try:
            # Handle different field names between Facebook and Instagram
            url = post.get("url") or post.get("post_url") or post.get("link", "")
            content = post.get("text") or post.get("caption") or post.get("message", "")

            # Skip posts without content
            if not content or len(content) < 10:
                return None

            # Skip if no URL
            if not url:
                url = f"https://www.{self.source.platform}.com/{self.source.account_id}"

            # Parse date
            published_at = None
            date_str = post.get("date") or post.get("timestamp") or post.get("created_time")
            if date_str:
                try:
                    if isinstance(date_str, (int, float)):
                        published_at = datetime.fromtimestamp(date_str)
                    else:
                        from dateutil import parser
                        published_at = parser.parse(date_str)
                except:
                    pass

            # Get image URL
            image_url = (
                post.get("image_url") or
                post.get("thumbnail_url") or
                post.get("full_picture")
            )
            if isinstance(image_url, list) and image_url:
                image_url = image_url[0]

            return ScrapedItem(
                url=url,
                title=None,  # Social posts don't have titles
                content=self.clean_text(content),
                source_name=self.source.name,
                source_type="social",
                source_platform=self.source.platform,
                image_url=image_url,
                published_at=published_at,
                county=self.source.county.value if self.source.county else None,
                raw_data=post
            )

        except Exception as e:
            self.logger.warning(f"Error parsing post: {e}")
            return None

    async def health_check(self) -> bool:
        """Verify Bright Data API is accessible."""
        if not self.is_configured():
            return False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/datasets",
                    headers=self.headers
                )
                return response.status_code == 200
        except:
            return False
