"""
Pydantic models for database records.
"""
from datetime import datetime, date, time
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class FilterStatus(str, Enum):
    """Content filter status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class NewsletterStatus(str, Enum):
    """Newsletter delivery status."""
    DRAFT = "draft"
    PREVIEW_SENT = "preview_sent"
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"


class ScrapeRunStatus(str, Enum):
    """Scrape run status."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScrapedContentCreate(BaseModel):
    """Model for creating scraped content."""
    url: str
    url_hash: str
    source_name: str
    source_type: str
    source_platform: Optional[str] = None
    title: Optional[str] = None
    content: str
    image_url: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    county: Optional[str] = None


class ScrapedContent(ScrapedContentCreate):
    """Model for scraped content from database."""
    id: int
    summary: Optional[str] = None
    content_category: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    is_event: bool = False
    event_date: Optional[date] = None
    event_time: Optional[time] = None
    event_location: Optional[str] = None
    filter_status: FilterStatus = FilterStatus.PENDING
    filter_reason: Optional[str] = None
    scraped_at: datetime
    filtered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FilterResult(BaseModel):
    """Model for content filter results."""
    decision: FilterStatus
    reason: str
    sentiment: str
    sentiment_score: float
    is_event: bool
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    event_location: Optional[str] = None
    category: str
    county: Optional[str] = None
    summary: str


class NewsletterCreate(BaseModel):
    """Model for creating a newsletter."""
    subject_line: str
    top_story_content: Optional[str] = None
    top_story_source_id: Optional[int] = None
    html_content: str
    plain_text_content: Optional[str] = None
    total_items: int = 0
    nash_county_items: int = 0
    edgecombe_county_items: int = 0
    wilson_county_items: int = 0
    event_count: int = 0


class Newsletter(NewsletterCreate):
    """Model for newsletter from database."""
    id: int
    newsletter_id: str
    mailchimp_campaign_id: Optional[str] = None
    mailchimp_campaign_web_id: Optional[str] = None
    status: NewsletterStatus = NewsletterStatus.DRAFT
    preview_sent_to: Optional[str] = None
    preview_sent_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    recipients_count: Optional[int] = None
    opens_count: Optional[int] = None
    clicks_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScrapeRunCreate(BaseModel):
    """Model for creating a scrape run."""
    source_name: Optional[str] = None
    source_type: Optional[str] = None


class ScrapeRun(ScrapeRunCreate):
    """Model for scrape run from database."""
    id: int
    run_id: str
    status: ScrapeRunStatus = ScrapeRunStatus.RUNNING
    items_found: int = 0
    items_new: int = 0
    items_duplicate: int = 0
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApprovedContent(BaseModel):
    """Model for approved content ready for newsletter."""
    id: int
    title: Optional[str]
    summary: str
    url: str
    source_name: str
    county: Optional[str]
    category: str
    is_event: bool
    event_date: Optional[str] = None
    event_time: Optional[str] = None
    event_location: Optional[str] = None
    content: str  # Full content for top story generation
