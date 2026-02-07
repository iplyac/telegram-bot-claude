"""Tests for PromptReloadCommand."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx

from tgbot.commands.promptreload import PromptReloadCommand


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update."""
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 123456
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create a mock bot context."""
    return MagicMock()


class TestPromptReloadCommand:
    """Tests for PromptReloadCommand class."""

    def test_name(self):
        """Command name should be 'promptreload'."""
        cmd = PromptReloadCommand(agent_api_url="https://example.com")
        assert cmd.name == "promptreload"

    def test_description(self):
        """Command should have a description."""
        cmd = PromptReloadCommand(agent_api_url="https://example.com")
        assert cmd.description != ""


class TestSuccessScenario:
    """Tests for successful prompt reload."""

    @pytest.mark.asyncio
    async def test_success_response(self, mock_update, mock_context):
        """Should display success message with prompt length."""
        cmd = PromptReloadCommand(agent_api_url="https://example.com")

        with patch("tgbot.commands.promptreload.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"status": "ok", "prompt_length": 207}
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            await cmd.handle(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once_with(
                "Prompt reloaded successfully (207 characters)"
            )


class TestApiErrorScenario:
    """Tests for API error responses."""

    @pytest.mark.asyncio
    async def test_api_error_response(self, mock_update, mock_context):
        """Should display error message from API."""
        cmd = PromptReloadCommand(agent_api_url="https://example.com")

        with patch("tgbot.commands.promptreload.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "error",
                "error": "AGENT_PROMPT_ID not configured",
            }
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            await cmd.handle(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once_with(
                "Failed to reload prompt: AGENT_PROMPT_ID not configured"
            )


class TestBackendNotConfigured:
    """Tests for backend not configured scenario."""

    @pytest.mark.asyncio
    async def test_backend_not_configured(self, mock_update, mock_context):
        """Should reply with error when backend not configured."""
        cmd = PromptReloadCommand(agent_api_url=None)

        await cmd.handle(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            "Prompt reload unavailable - backend not configured"
        )

    @pytest.mark.asyncio
    async def test_http_error(self, mock_update, mock_context):
        """Should reply with error on HTTP failure."""
        cmd = PromptReloadCommand(agent_api_url="https://example.com")

        with patch("tgbot.commands.promptreload.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            await cmd.handle(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "Failed to reload prompt" in call_args
