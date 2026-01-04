"""
Logging configuration with sensitive data filtering.
"""
import logging
import sys
import re
from typing import Dict


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


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure application logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create formatter
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

    logging.info(f"Logging configured at {log_level} level")
