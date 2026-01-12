"""
FastAPI application setup.
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from config.settings import get_settings
from config.logging_config import setup_logging
from database.connection import init_database, close_database
from database.schema import DatabaseSchema
from api.routes import health, admin, webhooks
from api.middleware import RequestIDMiddleware

logger = logging.getLogger(__name__)

# Global scheduler reference
_scheduler = None

# Prometheus metrics - exported for use in other modules
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)
SCRAPE_COUNT = Counter(
    "scrape_items_total",
    "Total items scraped",
    ["source_type", "status"]
)
FILTER_COUNT = Counter(
    "filter_decisions_total",
    "Content filter decisions",
    ["decision"]
)
NEWSLETTER_COUNT = Counter(
    "newsletters_total",
    "Newsletters sent",
    ["status"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global _scheduler

    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info("Starting TwinCountyMediaAgent...")

    # Initialize database
    db = init_database(settings)
    await db.connect()

    # Create database tables
    schema = DatabaseSchema(db.pool)
    await schema.create_all_tables()

    # Start scheduler
    from services.scheduler import SchedulerService
    _scheduler = SchedulerService(db)
    _scheduler.start()

    logger.info("TwinCountyMediaAgent started successfully")

    yield

    # Shutdown
    logger.info("Shutting down TwinCountyMediaAgent...")

    if _scheduler:
        _scheduler.shutdown()

    await close_database()

    logger.info("TwinCountyMediaAgent shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="TwinCountyMediaAgent",
        description="Local News & Community Newsletter Agent for Nash, Edgecombe, and Wilson Counties",
        version="1.0.0",
        lifespan=lifespan
    )

    # Request ID tracking middleware (add first so it's executed last)
    app.add_middleware(RequestIDMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(admin.router, prefix="/api/v1/admin")
    app.include_router(webhooks.router, prefix="/api/v1/webhooks")

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": "TwinCountyMediaAgent",
            "version": "1.0.0",
            "description": "Local News & Community Newsletter Agent",
            "coverage": ["Nash County", "Edgecombe County", "Wilson County"],
            "status": "running"
        }

    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )

    return app


# Create the app instance
app = create_app()
