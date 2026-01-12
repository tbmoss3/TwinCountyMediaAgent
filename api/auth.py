"""
API authentication and authorization.
"""
import secrets
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from config.settings import get_settings

# API key header definition
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Verify the API key for admin endpoints.

    In development without admin_api_key configured, authentication is bypassed.
    In production, admin_api_key is required.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        The verified API key

    Raises:
        HTTPException: If authentication fails
    """
    settings = get_settings()

    # If no API key is configured and not in production, allow access
    if not settings.requires_api_auth:
        return "development-bypass"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(api_key, settings.admin_api_key or ""):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key
