"""
Application entry point.
"""
import uvicorn
from config.settings import get_settings


def main():
    """Run the application."""
    settings = get_settings()

    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
