"""Tests for PromptReloadCommand."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx

from tgbot.commands.promptreload import PromptReloadCommand
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


class TestPromptReloadCommand:
    def test_name(self):
        cmd = PromptReloadCommand(make_backend())
        assert cmd.name == "promptreload"

    def test_description(self):
        cmd = PromptReloadCommand(make_backend())
        assert cmd.description != ""


class TestSuccessScenario:
    @pytest.mark.asyncio
    async def test_success_response(self, mock_update, mock_context):
        backend = make_backend()
        cmd = PromptReloadCommand(backend)

        with patch.object(
            backend, "reload_prompt",
            new_callable=AsyncMock,
            return_value={"status": "ok", "prompt_length": 207},
        ):
            await cmd.handle(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            "Prompt reloaded successfully (207 characters)"
        )

    @pytest.mark.asyncio
    async def test_api_error_response(self, mock_update, mock_context):
        backend = make_backend()
        cmd = PromptReloadCommand(backend)

        with patch.object(
            backend, "reload_prompt",
            new_callable=AsyncMock,
            return_value={"status": "error", "error": "AGENT_PROMPT_ID not configured"},
        ):
            await cmd.handle(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            "Failed to reload prompt: AGENT_PROMPT_ID not configured"
        )


class TestAdminAccessControl:
    @pytest.mark.asyncio
    async def test_unauthorized_user_rejected(self, mock_update, mock_context):
        """Non-admin users should be rejected when ADMIN_USER_IDS is configured."""
        backend = make_backend()
        cmd = PromptReloadCommand(backend)

        with patch("tgbot.commands.promptreload._ADMIN_USER_IDS", frozenset({999999})):
            await cmd.handle(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with("Unauthorized.")

    @pytest.mark.asyncio
    async def test_authorized_user_allowed(self, mock_update, mock_context):
        """Admin user (id=123456) should be allowed through."""
        backend = make_backend()
        cmd = PromptReloadCommand(backend)

        with patch("tgbot.commands.promptreload._ADMIN_USER_IDS", frozenset({123456})):
            with patch.object(
                backend, "reload_prompt",
                new_callable=AsyncMock,
                return_value={"status": "ok", "prompt_length": 100},
            ):
                await cmd.handle(mock_update, mock_context)

        reply_text = mock_update.message.reply_text.call_args[0][0]
        assert "reloaded successfully" in reply_text

    @pytest.mark.asyncio
    async def test_empty_admin_ids_allows_all(self, mock_update, mock_context):
        """Empty ADMIN_USER_IDS means no restriction."""
        backend = make_backend()
        cmd = PromptReloadCommand(backend)

        with patch("tgbot.commands.promptreload._ADMIN_USER_IDS", frozenset()):
            with patch.object(
                backend, "reload_prompt",
                new_callable=AsyncMock,
                return_value={"status": "ok", "prompt_length": 50},
            ):
                await cmd.handle(mock_update, mock_context)

        reply_text = mock_update.message.reply_text.call_args[0][0]
        assert "reloaded successfully" in reply_text


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_backend_not_configured(self, mock_update, mock_context):
        cmd = PromptReloadCommand(BackendClient(agent_api_url=None))

        await cmd.handle(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            "Prompt reload unavailable - backend not configured"
        )

    @pytest.mark.asyncio
    async def test_http_error_shows_generic_message(self, mock_update, mock_context):
        """HTTP error should show a safe generic message, not the raw exception."""
        backend = make_backend()
        cmd = PromptReloadCommand(backend)

        with patch.object(
            backend, "reload_prompt",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            await cmd.handle(mock_update, mock_context)

        call_text = mock_update.message.reply_text.call_args[0][0]
        assert "Failed to reload prompt" in call_text
        assert "Connection refused" not in call_text  # no raw error leakage
