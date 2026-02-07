"""Tests for GetPromptCommand."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx

from tgbot.commands.getprompt import GetPromptCommand, MAX_PROMPT_DISPLAY_LENGTH


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


class TestGetPromptCommand:
    """Tests for GetPromptCommand class."""

    def test_name(self):
        """Command name should be 'getprompt'."""
        cmd = GetPromptCommand(agent_api_url="https://example.com")
        assert cmd.name == "getprompt"

    def test_description(self):
        """Command should have a description."""
        cmd = GetPromptCommand(agent_api_url="https://example.com")
        assert cmd.description != ""


class TestSuccessScenario:
    """Tests for successful prompt retrieval."""

    @pytest.mark.asyncio
    async def test_success_short_prompt(self, mock_update, mock_context):
        """Should display prompt with length in code block."""
        cmd = GetPromptCommand(agent_api_url="https://example.com")

        with patch("tgbot.commands.getprompt.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "prompt": "You are a helpful AI assistant.",
                "length": 33,
            }
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            await cmd.handle(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "Current prompt (33 characters):" in call_args
            assert "You are a helpful AI assistant." in call_args
            assert "```" in call_args

    @pytest.mark.asyncio
    async def test_success_long_prompt_truncated(self, mock_update, mock_context):
        """Should truncate prompt longer than MAX_PROMPT_DISPLAY_LENGTH."""
        cmd = GetPromptCommand(agent_api_url="https://example.com")

        long_prompt = "A" * 5000
        with patch("tgbot.commands.getprompt.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "prompt": long_prompt,
                "length": 5000,
            }
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            await cmd.handle(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "5000 characters, truncated" in call_args
            assert "..." in call_args
            # Check prompt was actually truncated
            assert len(call_args) < 5000 + 100  # Some room for formatting


class TestApiErrorScenario:
    """Tests for API error responses."""

    @pytest.mark.asyncio
    async def test_http_error(self, mock_update, mock_context):
        """Should reply with error on HTTP failure."""
        cmd = GetPromptCommand(agent_api_url="https://example.com")

        with patch("tgbot.commands.getprompt.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            await cmd.handle(mock_update, mock_context)

            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "Failed to get prompt" in call_args


class TestBackendNotConfigured:
    """Tests for backend not configured scenario."""

    @pytest.mark.asyncio
    async def test_backend_not_configured(self, mock_update, mock_context):
        """Should reply with error when backend not configured."""
        cmd = GetPromptCommand(agent_api_url=None)

        await cmd.handle(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            "Get prompt unavailable - backend not configured"
        )
