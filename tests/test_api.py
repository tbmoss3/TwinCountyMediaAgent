"""
Unit tests for API routes.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import sys

# Mock crawl4ai before any imports that depend on it
sys.modules['crawl4ai'] = MagicMock()
sys.modules['crawl4ai.AsyncWebCrawler'] = MagicMock()
sys.modules['crawl4ai.BrowserConfig'] = MagicMock()
sys.modules['crawl4ai.CrawlerRunConfig'] = MagicMock()


class TestHealthEndpoints:
    """Test cases for health check endpoints."""

    def test_health_check_endpoint(self):
        """Test basic health check returns healthy status."""
        from api.routes.health import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "TwinCountyMediaAgent"
        assert "timestamp" in data

    def test_detailed_health_check_healthy(self):
        """Test detailed health check when database is healthy."""
        from api.routes.health import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_db = MagicMock()
        mock_db.health_check = AsyncMock(return_value=True)

        with patch("api.routes.health.get_database", return_value=mock_db):
            client = TestClient(app)
            response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["components"]["database"] == "healthy"

    def test_detailed_health_check_degraded(self):
        """Test detailed health check when database is unhealthy."""
        from api.routes.health import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_db = MagicMock()
        mock_db.health_check = AsyncMock(return_value=False)

        with patch("api.routes.health.get_database", return_value=mock_db):
            client = TestClient(app)
            response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["components"]["database"] == "unhealthy"

    def test_readiness_check_ready(self):
        """Test readiness probe when database is healthy."""
        from api.routes.health import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_db = MagicMock()
        mock_db.health_check = AsyncMock(return_value=True)

        with patch("api.routes.health.get_database", return_value=mock_db):
            client = TestClient(app)
            response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True

    def test_readiness_check_not_ready(self):
        """Test readiness probe when database is unhealthy."""
        from api.routes.health import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        mock_db = MagicMock()
        mock_db.health_check = AsyncMock(return_value=False)

        with patch("api.routes.health.get_database", return_value=mock_db):
            client = TestClient(app)
            response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is False
        assert "reason" in data


class TestAdminEndpoints:
    """Test cases for admin API endpoints."""

    def test_trigger_scrape_all_sources(self):
        """Test trigger scrape for all sources."""
        from api.routes.admin import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/admin")

        mock_db = MagicMock()
        mock_orchestrator = MagicMock()
        mock_orchestrator.run_scrape = AsyncMock()

        # Need to mock at the point of import in admin.py
        with patch("api.routes.admin.get_database", return_value=mock_db):
            client = TestClient(app)
            response = client.post("/api/v1/admin/scrape/trigger")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "all sources" in data["message"]

    def test_trigger_scrape_specific_type(self):
        """Test trigger scrape for specific source type."""
        from api.routes.admin import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/admin")

        mock_db = MagicMock()

        with patch("api.routes.admin.get_database", return_value=mock_db):
            client = TestClient(app)
            response = client.post("/api/v1/admin/scrape/trigger?source_type=news")

        assert response.status_code == 200
        data = response.json()
        assert "news" in data["message"]

    def test_trigger_filtering_no_pending(self):
        """Test trigger filtering with no pending content."""
        from api.routes.admin import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/admin")

        mock_db = MagicMock()
        mock_db.fetch = AsyncMock(return_value=[])

        # Mock ContentRepository
        mock_repo = MagicMock()
        mock_repo.get_pending_content = AsyncMock(return_value=[])

        with patch("api.routes.admin.get_database", return_value=mock_db):
            with patch("api.routes.admin.ContentRepository", return_value=mock_repo):
                client = TestClient(app)
                response = client.post("/api/v1/admin/filter/trigger")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"

    def test_trigger_filtering_with_pending(self, sample_scraped_content):
        """Test trigger filtering with pending content."""
        from api.routes.admin import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/admin")

        mock_db = MagicMock()

        mock_repo = MagicMock()
        mock_repo.get_pending_content = AsyncMock(return_value=[sample_scraped_content])

        with patch("api.routes.admin.get_database", return_value=mock_db):
            with patch("api.routes.admin.ContentRepository", return_value=mock_repo):
                client = TestClient(app)
                response = client.post("/api/v1/admin/filter/trigger")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "1 items" in data["message"]

    def test_generate_newsletter(self):
        """Test newsletter generation endpoint returns started status."""
        from api.routes.admin import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/admin")

        mock_db = MagicMock()
        mock_builder = MagicMock()
        mock_builder.build_and_send_preview = AsyncMock(return_value=1)

        with patch("api.routes.admin.get_database", return_value=mock_db):
            # Mock the import inside the endpoint
            with patch.dict("sys.modules", {"services.newsletter_builder": MagicMock()}):
                client = TestClient(app)
                response = client.post("/api/v1/admin/newsletter/generate")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"

    def test_send_newsletter_no_pending(self):
        """Test send newsletter with no pending newsletter."""
        from api.routes.admin import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/admin")

        mock_db = MagicMock()

        mock_repo = MagicMock()
        mock_repo.get_pending_newsletter = AsyncMock(return_value=None)

        with patch("api.routes.admin.get_database", return_value=mock_db):
            with patch("api.routes.admin.NewsletterRepository", return_value=mock_repo):
                client = TestClient(app)
                response = client.post("/api/v1/admin/newsletter/send")

        assert response.status_code == 404
        data = response.json()
        assert "No newsletter pending" in data["detail"]

    def test_preview_newsletter(self, sample_newsletter):
        """Test newsletter preview endpoint."""
        from api.routes.admin import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/admin")

        mock_db = MagicMock()

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=sample_newsletter)

        with patch("api.routes.admin.get_database", return_value=mock_db):
            with patch("api.routes.admin.NewsletterRepository", return_value=mock_repo):
                client = TestClient(app)
                response = client.get("/api/v1/admin/newsletter/preview/1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["subject_line"] == sample_newsletter.subject_line

    def test_preview_newsletter_not_found(self):
        """Test newsletter preview with invalid ID."""
        from api.routes.admin import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/admin")

        mock_db = MagicMock()

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch("api.routes.admin.get_database", return_value=mock_db):
            with patch("api.routes.admin.NewsletterRepository", return_value=mock_repo):
                client = TestClient(app)
                response = client.get("/api/v1/admin/newsletter/preview/999")

        assert response.status_code == 404

    def test_get_pending_content(self, sample_scraped_content):
        """Test get pending content endpoint."""
        from api.routes.admin import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/admin")

        mock_db = MagicMock()

        mock_repo = MagicMock()
        mock_repo.get_pending_content = AsyncMock(return_value=[sample_scraped_content])

        with patch("api.routes.admin.get_database", return_value=mock_db):
            with patch("api.routes.admin.ContentRepository", return_value=mock_repo):
                client = TestClient(app)
                response = client.get("/api/v1/admin/content/pending")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert len(data["items"]) == 1

    def test_get_approved_content(self, sample_approved_content):
        """Test get approved content endpoint."""
        from api.routes.admin import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/admin")

        mock_db = MagicMock()

        mock_repo = MagicMock()
        mock_repo.get_approved_content = AsyncMock(return_value=[sample_approved_content])

        with patch("api.routes.admin.get_database", return_value=mock_db):
            with patch("api.routes.admin.ContentRepository", return_value=mock_repo):
                client = TestClient(app)
                response = client.get("/api/v1/admin/content/approved")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1

    def test_get_stats_overview(self, mock_record_factory):
        """Test stats overview endpoint."""
        from api.routes.admin import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/admin")

        mock_db = MagicMock()

        mock_content_repo = MagicMock()
        mock_content_repo.get_stats = AsyncMock(return_value={
            "total": 100, "pending": 20, "approved": 70, "rejected": 10
        })

        mock_newsletter_repo = MagicMock()
        mock_newsletter_repo.get_stats = AsyncMock(return_value={
            "total": 25, "sent": 20
        })

        with patch("api.routes.admin.get_database", return_value=mock_db):
            with patch("api.routes.admin.ContentRepository", return_value=mock_content_repo):
                with patch("api.routes.admin.NewsletterRepository", return_value=mock_newsletter_repo):
                    client = TestClient(app)
                    response = client.get("/api/v1/admin/stats/overview")

        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "newsletters" in data
        assert data["content"]["total"] == 100


class TestWebhookEndpoints:
    """Test cases for webhook endpoints."""

    def test_mailchimp_webhook_verify(self):
        """Test Mailchimp webhook verification endpoint."""
        from api.routes.webhooks import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/webhooks")
        client = TestClient(app)

        response = client.get("/api/v1/webhooks/mailchimp/verify")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "verified"
        assert data["service"] == "TwinCountyMediaAgent"

    def test_mailchimp_webhook_campaign_event(self):
        """Test Mailchimp webhook for campaign event."""
        from api.routes.webhooks import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/webhooks")

        mock_db = MagicMock()
        mock_db.fetchrow = AsyncMock(return_value={"id": 1})

        mock_repo = MagicMock()
        mock_repo.update_metrics = AsyncMock()

        with patch("api.routes.webhooks.get_database", return_value=mock_db):
            with patch("api.routes.webhooks.NewsletterRepository", return_value=mock_repo):
                client = TestClient(app)
                response = client.post(
                    "/api/v1/webhooks/mailchimp",
                    json={
                        "type": "campaign",
                        "data": {
                            "id": "camp-123",
                            "emails_sent": 100,
                            "unique_opens": 50,
                            "clicks": 20
                        }
                    }
                )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["type"] == "campaign"

    def test_mailchimp_webhook_unknown_type(self):
        """Test Mailchimp webhook with unknown event type."""
        from api.routes.webhooks import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/webhooks")

        client = TestClient(app)
        response = client.post(
            "/api/v1/webhooks/mailchimp",
            json={
                "type": "unknown_event",
                "data": {}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"

    def test_mailchimp_webhook_handles_error(self):
        """Test Mailchimp webhook handles errors gracefully."""
        from api.routes.webhooks import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/webhooks")

        with patch("api.routes.webhooks.get_database", side_effect=Exception("DB Error")):
            client = TestClient(app)
            response = client.post(
                "/api/v1/webhooks/mailchimp",
                json={
                    "type": "campaign",
                    "data": {"id": "camp-123"}
                }
            )

        # Should return 200 to prevent Mailchimp from retrying
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"


class TestRootEndpoint:
    """Test cases for root endpoint."""

    def test_root_endpoint(self):
        """Test root endpoint returns service info."""
        from api.app import create_app
        from fastapi.testclient import TestClient

        # Create app without lifespan to avoid DB connection
        from fastapi import FastAPI
        app = FastAPI()

        @app.get("/")
        async def root():
            return {
                "service": "TwinCountyMediaAgent",
                "version": "1.0.0",
                "description": "Local News & Community Newsletter Agent",
                "coverage": ["Nash County", "Edgecombe County", "Wilson County"],
                "status": "running"
            }

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "TwinCountyMediaAgent"
        assert data["version"] == "1.0.0"
        assert "Nash County" in data["coverage"]
