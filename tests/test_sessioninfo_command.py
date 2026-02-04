"""Tests for SessionInfoCommand."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx

from tgbot.commands.sessioninfo import SessionInfoCommand


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
    """Create a mock bot context."""
    return MagicMock()


class TestSessionInfoCommand:
    """Tests for SessionInfoCommand class."""

    def test_name(self):
        """Command name should be 'sessioninfo'."""
        cmd = SessionInfoCommand(agent_api_url="https://example.com")
        assert cmd.name == "sessioninfo"

    def test_description(self):
        """Command should have a description."""
        cmd = SessionInfoCommand(agent_api_url="https://example.com")
        assert cmd.description != ""


class TestConversationIdDerivation:
    """Tests for conversation_id derivation."""

    @pytest.mark.asyncio
    async def test_private_chat_conversation_id(self, mock_update_private, mock_context):
        """Private chat should use tg_dm_{chat_id} format."""
        cmd = SessionInfoCommand(agent_api_url="https://example.com")

        with patch("tgbot.commands.sessioninfo.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"session_exists": False}
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            await cmd.handle(mock_update_private, mock_context)

            # Verify POST was called with correct conversation_id
            mock_instance.post.assert_called_once()
            call_kwargs = mock_instance.post.call_args
            assert call_kwargs[1]["json"]["conversation_id"] == "tg_dm_123456"

    @pytest.mark.asyncio
    async def test_group_chat_conversation_id(self, mock_update_group, mock_context):
        """Group chat should use tg_group_{chat_id} format."""
        cmd = SessionInfoCommand(agent_api_url="https://example.com")

        with patch("tgbot.commands.sessioninfo.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"session_exists": False}
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            await cmd.handle(mock_update_group, mock_context)

            # Verify POST was called with correct conversation_id
            mock_instance.post.assert_called_once()
            call_kwargs = mock_instance.post.call_args
            assert call_kwargs[1]["json"]["conversation_id"] == "tg_group_789012"


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_backend_not_configured(self, mock_update_private, mock_context):
        """Should reply with error when backend not configured."""
        cmd = SessionInfoCommand(agent_api_url=None)

        await cmd.handle(mock_update_private, mock_context)

        mock_update_private.message.reply_text.assert_called_once_with(
            "Session info unavailable - backend not configured"
        )

    @pytest.mark.asyncio
    async def test_http_error(self, mock_update_private, mock_context):
        """Should reply with error on HTTP failure."""
        cmd = SessionInfoCommand(agent_api_url="https://example.com")

        with patch("tgbot.commands.sessioninfo.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            await cmd.handle(mock_update_private, mock_context)

            mock_update_private.message.reply_text.assert_called_once()
            call_args = mock_update_private.message.reply_text.call_args[0][0]
            assert "Failed to get session info" in call_args

    @pytest.mark.asyncio
    async def test_invalid_response(self, mock_update_private, mock_context):
        """Should reply with error on invalid response."""
        cmd = SessionInfoCommand(agent_api_url="https://example.com")

        with patch("tgbot.commands.sessioninfo.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"unexpected": "data"}
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            await cmd.handle(mock_update_private, mock_context)

            mock_update_private.message.reply_text.assert_called_once_with(
                "Failed to get session info: invalid response"
            )


class TestSessionDisplay:
    """Tests for session info display."""

    @pytest.mark.asyncio
    async def test_active_session_with_message_count(self, mock_update_private, mock_context):
        """Should display session info with message count."""
        cmd = SessionInfoCommand(agent_api_url="https://example.com")

        with patch("tgbot.commands.sessioninfo.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "conversation_id": "tg_dm_123456",
                "session_id": "tg_dm_123456",
                "session_exists": True,
                "message_count": 5,
            }
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            await cmd.handle(mock_update_private, mock_context)

            call_args = mock_update_private.message.reply_text.call_args
            text = call_args[0][0]
            assert "Session info:" in text
            assert "Active" in text
            assert "Messages: 5" in text

    @pytest.mark.asyncio
    async def test_no_active_session(self, mock_update_private, mock_context):
        """Should display no session message."""
        cmd = SessionInfoCommand(agent_api_url="https://example.com")

        with patch("tgbot.commands.sessioninfo.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "conversation_id": "tg_dm_123456",
                "session_id": "tg_dm_123456",
                "session_exists": False,
                "message_count": None,
            }
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            await cmd.handle(mock_update_private, mock_context)

            call_args = mock_update_private.message.reply_text.call_args
            text = call_args[0][0]
            assert "No active session" in text
