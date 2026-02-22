"""Tests for BackendClient identity token authentication."""

import logging
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from tgbot.services.backend_client import BackendClient


# ---------------------------------------------------------------------------
# _get_auth_headers tests (tasks 4.1, 4.2)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_auth_headers_success():
    """Returns Authorization header when fetch_id_token succeeds (task 4.1)."""
    client = BackendClient(agent_api_url="https://master-agent-example.run.app")

    with patch("google.oauth2.id_token.fetch_id_token", return_value="my-token") as mock_fetch:
        headers = await client._get_auth_headers()

    assert headers == {"Authorization": "Bearer my-token"}
    mock_fetch.assert_called_once()
    # Verify audience is the URL without trailing slash
    call_args = mock_fetch.call_args
    assert call_args[0][1] == "https://master-agent-example.run.app"


@pytest.mark.asyncio
async def test_get_auth_headers_strips_trailing_slash():
    """Audience must not have a trailing slash."""
    client = BackendClient(agent_api_url="https://master-agent-example.run.app/")

    with patch("google.oauth2.id_token.fetch_id_token", return_value="tok") as mock_fetch:
        await client._get_auth_headers()

    audience = mock_fetch.call_args[0][1]
    assert not audience.endswith("/")


@pytest.mark.asyncio
async def test_get_auth_headers_fetch_fails_returns_empty(caplog):
    """Returns {} and logs warning when fetch_id_token raises (task 4.2)."""
    client = BackendClient(agent_api_url="https://master-agent-example.run.app")

    with patch(
        "google.oauth2.id_token.fetch_id_token",
        side_effect=Exception("no metadata server"),
    ):
        with caplog.at_level(logging.WARNING, logger="tgbot.services.backend_client"):
            headers = await client._get_auth_headers()

    assert headers == {}
    assert any("Failed to fetch identity token" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_get_auth_headers_no_url_returns_empty():
    """Returns {} without attempting fetch when agent_api_url is None."""
    client = BackendClient(agent_api_url=None)

    with patch("google.oauth2.id_token.fetch_id_token") as mock_fetch:
        headers = await client._get_auth_headers()

    assert headers == {}
    mock_fetch.assert_not_called()


# ---------------------------------------------------------------------------
# _post_with_retry passes auth headers (task 4.3)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_with_retry_sends_auth_headers():
    """_post_with_retry passes auth headers from _get_auth_headers to httpx POST."""
    client = BackendClient(agent_api_url="https://master-agent-example.run.app")

    captured_headers = {}

    async def fake_post(url, *, json=None, headers=None, timeout=None):
        captured_headers.update(headers or {})
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"response": "ok"}
        mock_resp.status_code = 200
        return mock_resp

    client._client.post = fake_post

    with patch.object(
        client, "_get_auth_headers",
        new_callable=AsyncMock,
        return_value={"Authorization": "Bearer test-token"},
    ):
        result = await client._post_with_retry(
            "https://master-agent-example.run.app/api/chat",
            {"conversation_id": "x", "message": "hi"},
            session_id="x",
            log_label="test",
        )

    assert captured_headers.get("Authorization") == "Bearer test-token"
    assert result == {"response": "ok"}


@pytest.mark.asyncio
async def test_post_with_retry_no_auth_when_headers_empty():
    """When _get_auth_headers returns {}, POST is made without Authorization header."""
    client = BackendClient(agent_api_url="https://master-agent-example.run.app")

    captured_headers = {}

    async def fake_post(url, *, json=None, headers=None, timeout=None):
        captured_headers.update(headers or {})
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"response": "ok"}
        mock_resp.status_code = 200
        return mock_resp

    client._client.post = fake_post

    with patch.object(client, "_get_auth_headers", new_callable=AsyncMock, return_value={}):
        await client._post_with_retry(
            "https://master-agent-example.run.app/api/chat",
            {"conversation_id": "x", "message": "hi"},
            session_id="x",
            log_label="test",
        )

    assert "Authorization" not in captured_headers
