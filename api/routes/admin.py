"""
Admin API endpoints for manual triggers and monitoring.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from typing import Optional, Literal, List
from datetime import datetime
import logging

from api.auth import verify_api_key
from database.connection import get_database
from database.repositories.content_repository import ContentRepository
from database.repositories.newsletter_repository import NewsletterRepository

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"], dependencies=[Depends(verify_api_key)])

# Type alias for source types
SourceType = Literal["news", "social", "council"]


@router.post("/scrape/trigger")
async def trigger_scrape(
    background_tasks: BackgroundTasks,
    source_type: Optional[SourceType] = Query(
        default=None,
        description="Type of sources to scrape: 'news', 'social', or 'council'"
    )
):
    """
    Manually trigger content scraping.

    Args:
        source_type: Optional filter - 'news', 'social', or 'council'
    """
    # Import here to avoid circular imports
    from services.scraper_orchestrator import ScraperOrchestrator

    try:
        db = get_database()
        orchestrator = ScraperOrchestrator(db)

        # Run scraping in background
        background_tasks.add_task(orchestrator.run_scrape, source_type)

        return {
            "status": "started",
            "message": f"Scraping {'all sources' if not source_type else source_type} in background",
            "triggered_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error triggering scrape: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/filter/trigger")
async def trigger_filtering(background_tasks: BackgroundTasks):
    """Manually trigger content filtering."""
    from services.content_filter import ContentFilterService

    try:
        db = get_database()
        content_repo = ContentRepository(db)
        filter_service = ContentFilterService()

        # Get pending content count
        pending = await content_repo.get_pending_content(limit=1000)

        if not pending:
            return {
                "status": "skipped",
                "message": "No pending content to filter"
            }

        # Run filtering in background
        async def run_filtering():
            for content in pending:
                try:
                    result = await filter_service.filter_content(content)
                    await content_repo.update_filter_result(content.id, result)
                except Exception as e:
                    logger.error(f"Error filtering content {content.id}: {e}")

        background_tasks.add_task(run_filtering)

        return {
            "status": "started",
            "message": f"Filtering {len(pending)} items in background",
            "triggered_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error triggering filtering: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/newsletter/generate")
async def generate_newsletter(background_tasks: BackgroundTasks):
    """Manually generate newsletter (preview only)."""
    from services.newsletter_builder import NewsletterBuilderService

    try:
        db = get_database()
        builder = NewsletterBuilderService(db)

        # Run generation in background
        background_tasks.add_task(builder.build_and_send_preview)

        return {
            "status": "started",
            "message": "Newsletter generation started in background",
            "triggered_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating newsletter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/newsletter/send")
async def send_newsletter():
    """Manually send pending newsletter (bypass preview delay)."""
    from services.mailchimp_service import MailchimpService

    try:
        db = get_database()
        newsletter_repo = NewsletterRepository(db)
        mailchimp = MailchimpService()

        # Get pending newsletter
        pending = await newsletter_repo.get_pending_newsletter()

        if not pending:
            raise HTTPException(
                status_code=404,
                detail="No newsletter pending approval"
            )

        if not pending.mailchimp_campaign_id:
            raise HTTPException(
                status_code=400,
                detail="Newsletter has no Mailchimp campaign"
            )

        # Send immediately
        result = await mailchimp.send_campaign(pending.mailchimp_campaign_id)

        # Update status
        await newsletter_repo.update_status(
            pending.id,
            "sent",
            sent_at=datetime.now()
        )

        return {
            "status": "sent",
            "newsletter_id": pending.id,
            "campaign_id": pending.mailchimp_campaign_id,
            "sent_at": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending newsletter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/newsletter/preview/{newsletter_id}")
async def preview_newsletter(newsletter_id: int):
    """Get newsletter HTML preview."""
    try:
        db = get_database()
        newsletter_repo = NewsletterRepository(db)

        newsletter = await newsletter_repo.get_by_id(newsletter_id)

        if not newsletter:
            raise HTTPException(status_code=404, detail="Newsletter not found")

        return {
            "id": newsletter.id,
            "subject_line": newsletter.subject_line,
            "status": newsletter.status,
            "html_content": newsletter.html_content,
            "stats": {
                "total_items": newsletter.total_items,
                "nash_county": newsletter.nash_county_items,
                "edgecombe_county": newsletter.edgecombe_county_items,
                "wilson_county": newsletter.wilson_county_items,
                "events": newsletter.event_count
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting newsletter preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content/pending")
async def get_pending_content(
    limit: int = Query(default=50, ge=1, le=100, description="Maximum items to return"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip")
):
    """Get content pending filtering with pagination."""
    try:
        db = get_database()
        content_repo = ContentRepository(db)
        pending = await content_repo.get_pending_content(limit=limit, offset=offset)
        total = await content_repo.get_pending_count()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(pending),
            "items": [
                {
                    "id": c.id,
                    "title": c.title,
                    "source": c.source_name,
                    "scraped_at": c.scraped_at.isoformat()
                }
                for c in pending
            ]
        }
    except Exception as e:
        logger.error(f"Error getting pending content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content/approved")
async def get_approved_content(
    days: int = Query(default=7, ge=1, le=30, description="Days to look back"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum items to return"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip")
):
    """Get approved content for next newsletter with pagination."""
    try:
        db = get_database()
        content_repo = ContentRepository(db)
        approved = await content_repo.get_approved_content(days=days, limit=limit, offset=offset)
        total = await content_repo.get_approved_count(days=days)

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(approved),
            "items": [
                {
                    "id": c.id,
                    "title": c.title,
                    "summary": c.summary,
                    "source": c.source_name,
                    "county": c.county,
                    "is_event": c.is_event
                }
                for c in approved
            ]
        }
    except Exception as e:
        logger.error(f"Error getting approved content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/overview")
async def get_stats_overview():
    """Get system statistics overview."""
    try:
        db = get_database()
        content_repo = ContentRepository(db)
        newsletter_repo = NewsletterRepository(db)

        content_stats = await content_repo.get_stats()
        newsletter_stats = await newsletter_repo.get_stats()

        return {
            "content": content_stats,
            "newsletters": newsletter_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
