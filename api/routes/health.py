"""
Health check endpoints.
"""
import logging
from fastapi import APIRouter
from datetime import datetime

from database.connection import get_database

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "TwinCountyMediaAgent"
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with all component statuses."""
    components = {}

    # Check database
    try:
        db = get_database()
        db_healthy = await db.health_check()
        components["database"] = "healthy" if db_healthy else "unhealthy"
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        components["database"] = "unhealthy"

    # Check Claude API
    try:
        from services.content_filter import ContentFilterService
        filter_service = ContentFilterService()
        claude_healthy = await filter_service.health_check()
        components["claude_api"] = "healthy" if claude_healthy else "unhealthy"
    except Exception as e:
        logger.warning(f"Claude API health check failed: {e}")
        components["claude_api"] = "unhealthy"

    # Check Mailchimp
    try:
        from services.mailchimp_service import MailchimpService
        mailchimp_service = MailchimpService()
        mailchimp_healthy = await mailchimp_service.health_check()
        components["mailchimp"] = "healthy" if mailchimp_healthy else "unhealthy"
    except Exception as e:
        logger.warning(f"Mailchimp health check failed: {e}")
        components["mailchimp"] = "unhealthy"

    # Determine overall status
    all_healthy = all(v == "healthy" for v in components.values())
    critical_healthy = components.get("database") == "healthy"

    if all_healthy:
        status = "healthy"
    elif critical_healthy:
        status = "degraded"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "service": "TwinCountyMediaAgent",
        "components": components
    }


@router.get("/ready")
async def readiness_check():
    """Kubernetes-style readiness probe."""
    try:
        db = get_database()
        db_healthy = await db.health_check()
        if not db_healthy:
            return {"ready": False, "reason": "Database not healthy"}
    except Exception as e:
        return {"ready": False, "reason": str(e)}

    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """Kubernetes-style liveness probe."""
    return {"alive": True, "timestamp": datetime.now().isoformat()}
