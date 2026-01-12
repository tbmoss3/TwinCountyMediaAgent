"""
Database schema definitions and migration management.
"""
import logging
from typing import Optional
import asyncpg

logger = logging.getLogger(__name__)


# SQL schema definitions
SCHEMA_SQL = """
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: scraped_content
-- Stores all scraped content before and after filtering
CREATE TABLE IF NOT EXISTS scraped_content (
    id SERIAL PRIMARY KEY,
    url VARCHAR(2048) NOT NULL,
    url_hash VARCHAR(64) NOT NULL,  -- SHA256 for quick duplicate lookups

    -- Source Information
    source_name VARCHAR(100) NOT NULL,
    source_type VARCHAR(50) NOT NULL,   -- 'news', 'social', 'council'
    source_platform VARCHAR(50),         -- 'website', 'facebook', 'instagram'

    -- Content
    title TEXT,
    content TEXT NOT NULL,
    summary TEXT,                        -- AI-generated summary
    image_url VARCHAR(2048),
    author VARCHAR(255),
    published_at TIMESTAMP,

    -- Classification
    county VARCHAR(50),                  -- 'nash', 'edgecombe', 'wilson', null for regional
    content_category VARCHAR(100),       -- 'event', 'news', 'announcement', 'promotion'
    sentiment VARCHAR(20),               -- 'positive', 'neutral', 'negative'
    sentiment_score FLOAT,
    is_event BOOLEAN DEFAULT FALSE,

    -- Event Details (if applicable)
    event_date DATE,
    event_time TIME,
    event_location VARCHAR(500),

    -- Processing Status
    filter_status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    filter_reason TEXT,

    -- Timestamps
    scraped_at TIMESTAMP DEFAULT NOW(),
    filtered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Unique constraint on URL hash
    CONSTRAINT unique_url_hash UNIQUE (url_hash)
);

-- Indexes for scraped_content
CREATE INDEX IF NOT EXISTS idx_scraped_content_url_hash ON scraped_content(url_hash);
CREATE INDEX IF NOT EXISTS idx_scraped_content_source ON scraped_content(source_name, source_type);
CREATE INDEX IF NOT EXISTS idx_scraped_content_filter_status ON scraped_content(filter_status);
CREATE INDEX IF NOT EXISTS idx_scraped_content_county ON scraped_content(county);
CREATE INDEX IF NOT EXISTS idx_scraped_content_scraped_at ON scraped_content(scraped_at);
CREATE INDEX IF NOT EXISTS idx_scraped_content_is_event ON scraped_content(is_event);
CREATE INDEX IF NOT EXISTS idx_scraped_content_event_date ON scraped_content(event_date);

-- Table: sent_newsletters
-- Tracks newsletter generation and delivery
CREATE TABLE IF NOT EXISTS sent_newsletters (
    id SERIAL PRIMARY KEY,
    newsletter_id UUID DEFAULT uuid_generate_v4() UNIQUE,

    -- Newsletter Content
    subject_line VARCHAR(500) NOT NULL,
    top_story_content TEXT,
    top_story_source_id INT REFERENCES scraped_content(id),
    html_content TEXT NOT NULL,
    plain_text_content TEXT,

    -- Content Stats
    total_items INT DEFAULT 0,
    nash_county_items INT DEFAULT 0,
    edgecombe_county_items INT DEFAULT 0,
    wilson_county_items INT DEFAULT 0,
    event_count INT DEFAULT 0,

    -- Mailchimp Integration
    mailchimp_campaign_id VARCHAR(100),
    mailchimp_campaign_web_id VARCHAR(100),

    -- Delivery Status
    status VARCHAR(50) DEFAULT 'draft',  -- 'draft', 'preview_sent', 'scheduled', 'sent', 'failed'
    preview_sent_to VARCHAR(255),
    preview_sent_at TIMESTAMP,
    scheduled_for TIMESTAMP,
    sent_at TIMESTAMP,

    -- Metrics (populated via webhook)
    recipients_count INT,
    opens_count INT,
    clicks_count INT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for sent_newsletters
CREATE INDEX IF NOT EXISTS idx_sent_newsletters_status ON sent_newsletters(status);
CREATE INDEX IF NOT EXISTS idx_sent_newsletters_sent_at ON sent_newsletters(sent_at);
CREATE INDEX IF NOT EXISTS idx_sent_newsletters_created_at ON sent_newsletters(created_at);

-- Table: newsletter_content_links
-- Junction table linking newsletters to included content
CREATE TABLE IF NOT EXISTS newsletter_content_links (
    id SERIAL PRIMARY KEY,
    newsletter_id INT REFERENCES sent_newsletters(id) ON DELETE CASCADE,
    content_id INT REFERENCES scraped_content(id) ON DELETE CASCADE,
    section VARCHAR(50) NOT NULL,  -- 'top_story', 'news_links', 'calendar'
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_newsletter_content UNIQUE(newsletter_id, content_id)
);

-- Indexes for newsletter_content_links
CREATE INDEX IF NOT EXISTS idx_newsletter_content_newsletter ON newsletter_content_links(newsletter_id);
CREATE INDEX IF NOT EXISTS idx_newsletter_content_section ON newsletter_content_links(section);

-- Table: scrape_runs
-- Tracks scraping job executions
CREATE TABLE IF NOT EXISTS scrape_runs (
    id SERIAL PRIMARY KEY,
    run_id UUID DEFAULT uuid_generate_v4() UNIQUE,

    source_name VARCHAR(100),  -- NULL for full scrape
    source_type VARCHAR(50),

    -- Results
    status VARCHAR(50) DEFAULT 'running',  -- 'running', 'completed', 'failed'
    items_found INT DEFAULT 0,
    items_new INT DEFAULT 0,
    items_duplicate INT DEFAULT 0,
    error_message TEXT,

    -- Timing
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Indexes for scrape_runs
CREATE INDEX IF NOT EXISTS idx_scrape_runs_status ON scrape_runs(status);
CREATE INDEX IF NOT EXISTS idx_scrape_runs_started ON scrape_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_scrape_runs_source ON scrape_runs(source_name);

-- Table: source_configs
-- Dynamic source configuration (for enabling/disabling sources)
CREATE TABLE IF NOT EXISTS source_configs (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) UNIQUE NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    display_name VARCHAR(255) NOT NULL,

    -- Connection Details
    url VARCHAR(2048),
    platform VARCHAR(50),  -- For social media sources
    account_id VARCHAR(255),  -- For social media sources

    -- Scraping Config
    is_active BOOLEAN DEFAULT TRUE,
    scrape_frequency_hours INT DEFAULT 24,

    -- Classification
    default_county VARCHAR(50),

    last_scraped_at TIMESTAMP,
    last_error TEXT,
    consecutive_failures INT DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for source_configs
CREATE INDEX IF NOT EXISTS idx_source_configs_active ON source_configs(is_active);
CREATE INDEX IF NOT EXISTS idx_source_configs_type ON source_configs(source_type);

-- Table: system_state
-- Stores persistent system state (e.g., scheduler state)
CREATE TABLE IF NOT EXISTS system_state (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Initialize default system state
INSERT INTO system_state (key, value) VALUES ('scheduler', '{"pending_newsletter_id": null}')
ON CONFLICT (key) DO NOTHING;
"""


class DatabaseSchema:
    """Manages database schema creation and migrations."""

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize schema manager.

        Args:
            pool: AsyncPG connection pool
        """
        self.pool = pool

    async def create_all_tables(self) -> None:
        """Create all database tables."""
        logger.info("Creating database tables...")

        async with self.pool.acquire() as conn:
            # Split schema into individual statements and execute
            # This handles the extension creation which may need special handling
            statements = [s.strip() for s in SCHEMA_SQL.split(';') if s.strip()]

            for statement in statements:
                try:
                    await conn.execute(statement)
                except asyncpg.exceptions.DuplicateObjectError:
                    # Index or constraint already exists
                    pass
                except asyncpg.exceptions.DuplicateTableError:
                    # Table already exists
                    pass
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        logger.warning(f"Error executing statement: {e}")

        logger.info("Database tables created successfully")

    async def drop_all_tables(self) -> None:
        """Drop all database tables (use with caution)."""
        logger.warning("Dropping all database tables...")

        drop_sql = """
        DROP TABLE IF EXISTS newsletter_content_links CASCADE;
        DROP TABLE IF EXISTS sent_newsletters CASCADE;
        DROP TABLE IF EXISTS scrape_runs CASCADE;
        DROP TABLE IF EXISTS source_configs CASCADE;
        DROP TABLE IF EXISTS scraped_content CASCADE;
        """

        async with self.pool.acquire() as conn:
            await conn.execute(drop_sql)

        logger.info("All tables dropped")

    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = $1
        )
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, table_name)

    async def get_table_count(self, table_name: str) -> int:
        """Get row count for a table."""
        query = f"SELECT COUNT(*) FROM {table_name}"
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query)
