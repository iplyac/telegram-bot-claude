"""Tests for GetPromptCommand."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx

from tgbot.commands.getprompt import GetPromptCommand, MAX_PROMPT_DISPLAY_LENGTH
from tgbot.services.backend_client import BackendClient


def make_backend(url="https://example.com"):
    return BackendClient(agent_api_url=url)


@pytest.fixture
def mock_update():
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 123456
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    return MagicMock()


class TestGetPromptCommand:
    def test_name(self):
        cmd = GetPromptCommand(make_backend())
        assert cmd.name == "getprompt"

    def test_description(self):
        cmd = GetPromptCommand(make_backend())
        assert cmd.description != ""


class TestSuccessScenario:
    @pytest.mark.asyncio
    async def test_success_short_prompt(self, mock_update, mock_context):
        """Should display prompt with length in code block."""
        backend = make_backend()
        cmd = GetPromptCommand(backend)

        with patch.object(
            backend, "get_prompt",
            new_callable=AsyncMock,
            return_value={"prompt": "You are a helpful AI assistant.", "length": 33},
        ):
            await cmd.handle(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Current prompt (33 characters):" in call_args
        assert "You are a helpful AI assistant." in call_args
        assert "```" in call_args

    @pytest.mark.asyncio
    async def test_success_long_prompt_truncated(self, mock_update, mock_context):
        """Should truncate prompt longer than MAX_PROMPT_DISPLAY_LENGTH."""
        backend = make_backend()
        cmd = GetPromptCommand(backend)

        long_prompt = "A" * 5000
        with patch.object(
            backend, "get_prompt",
            new_callable=AsyncMock,
            return_value={"prompt": long_prompt, "length": 5000},
        ):
            await cmd.handle(mock_update, mock_context)

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "5000 characters, truncated" in call_args
        assert "..." in call_args
        assert len(call_args) < 5000 + 100

    @pytest.mark.asyncio
    async def test_reply_uses_markdown_parse_mode(self, mock_update, mock_context):
        """Reply should use Markdown parse mode for code block rendering."""
        backend = make_backend()
        cmd = GetPromptCommand(backend)

        with patch.object(
            backend, "get_prompt",
            new_callable=AsyncMock,
            return_value={"prompt": "Hello", "length": 5},
        ):
            await cmd.handle(mock_update, mock_context)

        call_kwargs = mock_update.message.reply_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "Markdown"


class TestAdminAccessControl:
    @pytest.mark.asyncio
    async def test_unauthorized_user_rejected(self, mock_update, mock_context):
        """Non-admin users should be rejected when ADMIN_USER_IDS is configured."""
        backend = make_backend()
        cmd = GetPromptCommand(backend)

        with patch("tgbot.commands.getprompt._ADMIN_USER_IDS", frozenset({999999})):
            await cmd.handle(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with("Unauthorized.")

    @pytest.mark.asyncio
    async def test_authorized_user_allowed(self, mock_update, mock_context):
        """Admin user (id=123456) should be allowed through."""
        backend = make_backend()
        cmd = GetPromptCommand(backend)

        with patch("tgbot.commands.getprompt._ADMIN_USER_IDS", frozenset({123456})):
            with patch.object(
                backend, "get_prompt",
                new_callable=AsyncMock,
                return_value={"prompt": "System prompt text.", "length": 18},
            ):
                await cmd.handle(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "System prompt text." in call_text

    @pytest.mark.asyncio
    async def test_empty_admin_ids_allows_all(self, mock_update, mock_context):
        """Empty ADMIN_USER_IDS means no restriction."""
        backend = make_backend()
        cmd = GetPromptCommand(backend)

        with patch("tgbot.commands.getprompt._ADMIN_USER_IDS", frozenset()):
            with patch.object(
                backend, "get_prompt",
                new_callable=AsyncMock,
                return_value={"prompt": "Prompt.", "length": 7},
            ):
                await cmd.handle(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Prompt." in call_text


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_backend_not_configured(self, mock_update, mock_context):
        cmd = GetPromptCommand(BackendClient(agent_api_url=None))

        await cmd.handle(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            "Get prompt unavailable - backend not configured"
        )

    @pytest.mark.asyncio
    async def test_http_error_shows_generic_message(self, mock_update, mock_context):
        """HTTP error should show a safe generic message, not the raw exception."""
        backend = make_backend()
        cmd = GetPromptCommand(backend)

        with patch.object(
            backend, "get_prompt",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            await cmd.handle(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Failed to get prompt" in call_text
        assert "Connection refused" not in call_text  # no raw error leakage
