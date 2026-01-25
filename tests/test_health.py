"""Tests for health check endpoints."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_config():
    """Mock configuration functions."""
    with patch("app.config") as mock:
        mock.get_project_id.return_value = "test-project"
        mock.get_log_level.return_value = "INFO"
        mock.get_region.return_value = "europe-west4"
        mock.get_service_name.return_value = "telegram-bot"
        mock.get_agent_api_url.return_value = None
        mock.get_webhook_url.return_value = None
        mock.get_webhook_path.return_value = "/telegram/webhook"
        mock.get_full_webhook_url.return_value = None
        mock.get_bot_token.return_value = "test-token-123"
        mock.get_webhook_secret.return_value = "test-secret-abc"
        mock.get_port.return_value = 8080
        yield mock


@pytest.fixture
def mock_telegram():
    """Mock Telegram bot components."""
    with patch("app.create_application") as mock_create, \
         patch("app.start_polling", new_callable=AsyncMock) as mock_polling, \
         patch("app.stop", new_callable=AsyncMock) as mock_stop, \
         patch("app.setup_handlers") as mock_handlers:

        # Create mock application
        mock_app = MagicMock()
        mock_app.bot = MagicMock()
        mock_app.update_queue = MagicMock()
        mock_app.shutdown = AsyncMock()
        mock_create.return_value = mock_app

        yield {
            "create_application": mock_create,
            "start_polling": mock_polling,
            "stop": mock_stop,
            "setup_handlers": mock_handlers,
            "app": mock_app,
        }


@pytest.fixture
def client(mock_config, mock_telegram):
    """Create test client with mocked dependencies."""
    from app import app
    with TestClient(app) as client:
        yield client


def test_healthz_returns_ok(client):
    """GET /healthz should return HTTP 200 with {"status": "ok"}."""
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_bot_reports_mode(client):
    """GET /healthz/bot should return bot status including mode and webhook_path."""
    response = client.get("/healthz/bot")

    assert response.status_code == 200
    data = response.json()

    assert "bot_running" in data
    assert "mode" in data
    assert "webhook_path" in data
    assert data["webhook_path"] == "/telegram/webhook"
    assert data["mode"] in ["polling", "webhook"]
