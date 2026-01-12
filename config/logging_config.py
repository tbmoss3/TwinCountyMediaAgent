"""
Logging configuration with sensitive data filtering and structlog support.
"""
import logging
import sys
import re
from typing import Any, Dict, Optional

import structlog


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in logs."""

    PATTERNS: Dict[str, str] = {
        r'sk-ant-[a-zA-Z0-9_-]+': 'sk-ant-***MASKED***',
        r'api[_-]?key["\']?\s*[:=]\s*["\']?[\w-]+': 'api_key=***MASKED***',
        r'password["\']?\s*[:=]\s*["\']?[^\s"\']+': 'password=***MASKED***',
        r'postgresql://[^:]+:([^@]+)@': r'postgresql://user:***MASKED***@',
        r'Bearer\s+[\w-]+': 'Bearer ***MASKED***',
    }

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data from log messages."""
        if hasattr(record, 'msg') and record.msg:
            msg = str(record.msg)
            for pattern, replacement in self.PATTERNS.items():
                msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
            record.msg = msg
        return True


def mask_sensitive_data(
    logger: logging.Logger,
    method_name: str,
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Structlog processor to mask sensitive data."""
    patterns = SensitiveDataFilter.PATTERNS

    def mask_value(value: Any) -> Any:
        if isinstance(value, str):
            for pattern, replacement in patterns.items():
                value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
        return value

    for key, value in event_dict.items():
        event_dict[key] = mask_value(value)

    return event_dict


def setup_logging(log_level: str = "INFO", use_json: bool = False) -> None:
    """
    Configure application logging with structlog support.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: If True, output JSON-formatted logs (for production)
    """
    # Configure structlog processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        mask_sensitive_data,
    ]

    if use_json:
        # JSON output for production/log aggregation
        processors = shared_processors + [
            structlog.processors.JSONRenderer()
        ]
    else:
        # Console output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure standard logging for third-party libraries
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    logging.info(f"Logging configured at {log_level} level")


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a structlog logger instance.

    Args:
        name: Logger name (optional)

    Returns:
        Bound structlog logger
    """
    return structlog.get_logger(name)
