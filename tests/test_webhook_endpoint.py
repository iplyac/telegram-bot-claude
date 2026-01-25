"""Tests for webhook endpoint."""

import asyncio
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
        mock.get_webhook_secret.return_value = "test-webhook-secret"
        mock.get_port.return_value = 8080
        yield mock


@pytest.fixture
def mock_telegram():
    """Mock Telegram bot components."""
    with patch("app.create_application") as mock_create, \
         patch("app.start_polling", new_callable=AsyncMock) as mock_polling, \
         patch("app.stop", new_callable=AsyncMock) as mock_stop, \
         patch("app.setup_handlers") as mock_handlers:

        # Create mock application with update queue
        mock_app = MagicMock()
        mock_app.bot = MagicMock()
        mock_app.update_queue = MagicMock()
        mock_app.update_queue.put_nowait = MagicMock()
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


def test_webhook_rejects_missing_secret_header(client):
    """Webhook should return 403 when secret header is missing."""
    payload = {"update_id": 123456789}

    response = client.post("/telegram/webhook", json=payload)

    assert response.status_code == 403


def test_webhook_rejects_wrong_secret_header(client):
    """Webhook should return 403 when secret header is wrong."""
    payload = {"update_id": 123456789}
    headers = {"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"}

    response = client.post("/telegram/webhook", json=payload, headers=headers)

    assert response.status_code == 403


def test_webhook_accepts_valid_secret_header(client, mock_telegram):
    """Webhook should return 200 when secret header is valid."""
    with patch("app.Update") as mock_update_class:
        mock_update = MagicMock()
        mock_update_class.de_json.return_value = mock_update

        payload = {"update_id": 123456789}
        headers = {"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"}

        response = client.post("/telegram/webhook", json=payload, headers=headers)

        assert response.status_code == 200


def test_webhook_invalid_json_returns_200(client):
    """Webhook should return 200 even with invalid JSON (no crash)."""
    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"}

    response = client.post(
        "/telegram/webhook",
        content="not valid json",
        headers={
            **headers,
            "Content-Type": "application/json",
        },
    )

    # Should return 200 to not expose errors to Telegram
    assert response.status_code == 200


def test_webhook_queue_full_returns_200(client, mock_telegram):
    """Webhook should return 200 even when queue is full."""
    with patch("app.Update") as mock_update_class:
        mock_update = MagicMock()
        mock_update_class.de_json.return_value = mock_update

        # Make put_nowait raise QueueFull
        mock_telegram["app"].update_queue.put_nowait.side_effect = asyncio.QueueFull()

        payload = {"update_id": 123456789}
        headers = {"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"}

        response = client.post("/telegram/webhook", json=payload, headers=headers)

        # Should still return 200
        assert response.status_code == 200


def test_webhook_enqueues_update(client, mock_telegram):
    """Webhook should enqueue update via put_nowait."""
    with patch("app.Update") as mock_update_class:
        mock_update = MagicMock()
        mock_update_class.de_json.return_value = mock_update

        payload = {"update_id": 123456789}
        headers = {"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"}

        response = client.post("/telegram/webhook", json=payload, headers=headers)

        assert response.status_code == 200
        # Verify put_nowait was called
        mock_telegram["app"].update_queue.put_nowait.assert_called_once_with(mock_update)
