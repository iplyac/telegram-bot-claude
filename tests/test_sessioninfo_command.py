"""Tests for SessionInfoCommand."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx

from tgbot.commands.sessioninfo import SessionInfoCommand
from tgbot.services.backend_client import BackendClient


def make_backend(url="https://example.com"):
    return BackendClient(agent_api_url=url)


@pytest.fixture
def mock_update_private():
    """Create a mock Telegram Update for private chat."""
    update = MagicMock()
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123456
    update.effective_chat.type = "private"
    update.effective_user = MagicMock()
    update.effective_user.id = 123456
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_update_group():
    """Create a mock Telegram Update for group chat."""
    update = MagicMock()
    update.effective_chat = MagicMock()
    update.effective_chat.id = 789012
    update.effective_chat.type = "group"
    update.effective_user = MagicMock()
    update.effective_user.id = 123456
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    return MagicMock()


class TestSessionInfoCommand:
    def test_name(self):
        cmd = SessionInfoCommand(make_backend())
        assert cmd.name == "sessioninfo"

    def test_description(self):
        cmd = SessionInfoCommand(make_backend())
        assert cmd.description != ""


class TestConversationIdDerivation:
    @pytest.mark.asyncio
    async def test_private_chat_uses_user_id(self, mock_update_private, mock_context):
        """Private chat should use tg_dm_{user_id} format."""
        backend = make_backend()
        cmd = SessionInfoCommand(backend)

        with patch.object(
            backend, "get_session_info",
            new_callable=AsyncMock,
            return_value={"session_exists": False},
        ) as mock_get:
            await cmd.handle(mock_update_private, mock_context)

        mock_get.assert_called_once_with("tg_dm_123456")

    @pytest.mark.asyncio
    async def test_group_chat_uses_chat_id(self, mock_update_group, mock_context):
        """Group chat should use tg_group_{chat_id} format."""
        backend = make_backend()
        cmd = SessionInfoCommand(backend)

        with patch.object(
            backend, "get_session_info",
            new_callable=AsyncMock,
            return_value={"session_exists": False},
        ) as mock_get:
            await cmd.handle(mock_update_group, mock_context)

        mock_get.assert_called_once_with("tg_group_789012")


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_backend_not_configured(self, mock_update_private, mock_context):
        cmd = SessionInfoCommand(BackendClient(agent_api_url=None))

        await cmd.handle(mock_update_private, mock_context)

        mock_update_private.message.reply_text.assert_called_once_with(
            "Session info unavailable - backend not configured"
        )

    @pytest.mark.asyncio
    async def test_http_error_shows_generic_message(self, mock_update_private, mock_context):
        """HTTP error should show a safe generic message, not the raw exception."""
        backend = make_backend()
        cmd = SessionInfoCommand(backend)

        with patch.object(
            backend, "get_session_info",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            await cmd.handle(mock_update_private, mock_context)

        call_text = mock_update_private.message.reply_text.call_args[0][0]
        assert "Failed to get session info" in call_text
        assert "Connection refused" not in call_text  # no raw error leakage

    @pytest.mark.asyncio
    async def test_invalid_response(self, mock_update_private, mock_context):
        backend = make_backend()
        cmd = SessionInfoCommand(backend)

        with patch.object(
            backend, "get_session_info",
            new_callable=AsyncMock,
            return_value={"unexpected": "data"},
        ):
            await cmd.handle(mock_update_private, mock_context)

        mock_update_private.message.reply_text.assert_called_once_with(
            "Failed to get session info: invalid response"
        )


class TestSessionDisplay:
    @pytest.mark.asyncio
    async def test_active_session_with_message_count(self, mock_update_private, mock_context):
        backend = make_backend()
        cmd = SessionInfoCommand(backend)

        with patch.object(
            backend, "get_session_info",
            new_callable=AsyncMock,
            return_value={
                "conversation_id": "tg_dm_123456",
                "session_id": "tg_dm_123456",
                "session_exists": True,
                "message_count": 5,
            },
        ):
            await cmd.handle(mock_update_private, mock_context)

        text = mock_update_private.message.reply_text.call_args[0][0]
        assert "Session info:" in text
        assert "Active" in text
        assert "Messages: 5" in text

    @pytest.mark.asyncio
    async def test_no_active_session(self, mock_update_private, mock_context):
        backend = make_backend()
        cmd = SessionInfoCommand(backend)

        with patch.object(
            backend, "get_session_info",
            new_callable=AsyncMock,
            return_value={
                "conversation_id": "tg_dm_123456",
                "session_exists": False,
            },
        ):
            await cmd.handle(mock_update_private, mock_context)

        text = mock_update_private.message.reply_text.call_args[0][0]
        assert "No active session" in text
