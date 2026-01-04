"""
Health check endpoints.
"""
from fastapi import APIRouter, Depends
from datetime import datetime

from database.connection import get_database, Database

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
    """Detailed health check with database status."""
    try:
        db = get_database()
        db_healthy = await db.health_check()
    except Exception:
        db_healthy = False

    return {
        "status": "healthy" if db_healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "service": "TwinCountyMediaAgent",
        "components": {
            "database": "healthy" if db_healthy else "unhealthy"
        }
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
