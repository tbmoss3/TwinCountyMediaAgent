"""
Custom middleware for the API.
"""
import uuid
import time
import logging
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Context variable for request ID - accessible throughout the request lifecycle
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    """Get the current request ID from context."""
    return request_id_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request ID tracking to all requests.

    Adds X-Request-ID header to responses and makes request ID
    available throughout the request lifecycle via context variable.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Get request ID from header or generate new one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store in context variable for use in logging
        token = request_id_var.set(request_id)

        # Add to request state for easy access in routes
        request.state.request_id = request_id

        # Track request timing
        start_time = time.time()

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            # Log request completion
            logger.info(
                f"Request completed | "
                f"request_id={request_id} | "
                f"method={request.method} | "
                f"path={request.url.path} | "
                f"status={response.status_code} | "
                f"duration_ms={duration_ms:.2f}"
            )

            return response

        finally:
            # Reset context variable
            request_id_var.reset(token)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log incoming requests with key details.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Log incoming request
        logger.debug(
            f"Request received | "
            f"method={request.method} | "
            f"path={request.url.path} | "
            f"client={request.client.host if request.client else 'unknown'}"
        )

        return await call_next(request)
