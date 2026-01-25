"""Tests for Telegram bot commands and message handling."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from tgbot.commands.start import StartCommand
from tgbot.commands.test import TestCommand
from tgbot.dispatcher import (
    _handle_text_message,
    _handle_unknown_command,
    MSG_AGENT_NOT_CONFIGURED,
    MSG_BACKEND_UNAVAILABLE,
    MSG_UNKNOWN_COMMAND,
)
from tgbot.services.backend_client import BackendClient


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update object."""
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 123456
    update.effective_user.first_name = "TestUser"
    update.message = MagicMock()
    update.message.text = "Hello, bot!"
    update.message.reply_text = AsyncMock()
    update.update_id = 987654321
    return update


@pytest.fixture
def mock_context():
    """Create a mock bot context."""
    return MagicMock()


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    """/start command should send a greeting message."""
    cmd = StartCommand()

    await cmd.handle(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]

    # Verify greeting contains expected elements
    assert "Hello" in call_args
    assert "TestUser" in call_args
    assert "/start" in call_args
    assert "/test" in call_args


@pytest.mark.asyncio
async def test_test_command_contains_hostname_and_time(mock_update, mock_context):
    """/test command should contain hostname and ISO-like local time with timezone."""
    cmd = TestCommand(
        project_id="test-project",
        region="europe-west4",
        service_name="telegram-bot",
    )

    with patch("tgbot.services.diagnostics.socket.gethostname", return_value="test-hostname"):
        await cmd.handle(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]

    # Verify contains hostname
    assert "test-hostname" in call_args

    # Verify contains time-like pattern (ISO format with timezone)
    assert "Local time:" in call_args
    # ISO format includes T and timezone offset like +00:00 or Z
    assert "T" in call_args or ":" in call_args


@pytest.mark.asyncio
async def test_message_no_agent_url(mock_update, mock_context):
    """Message without AGENT_API_URL should reply with configuration error."""
    backend_client = BackendClient(agent_api_url=None)

    await _handle_text_message(mock_update, mock_context, backend_client)

    mock_update.message.reply_text.assert_called_once_with(MSG_AGENT_NOT_CONFIGURED)


@pytest.mark.asyncio
async def test_message_with_agent_url_success(mock_update, mock_context):
    """Message with AGENT_API_URL should forward and return backend response."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    # Mock the forward_message method
    with patch.object(
        backend_client,
        "forward_message",
        new_callable=AsyncMock,
        return_value="Backend says hello!",
    ):
        await _handle_text_message(mock_update, mock_context, backend_client)

        mock_update.message.reply_text.assert_called_once_with("Backend says hello!")


@pytest.mark.asyncio
async def test_message_with_agent_url_failure(mock_update, mock_context):
    """Message with backend failure should reply with error message."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    # Mock forward_message to raise an exception
    with patch.object(
        backend_client,
        "forward_message",
        new_callable=AsyncMock,
        side_effect=Exception("Connection failed"),
    ):
        await _handle_text_message(mock_update, mock_context, backend_client)

        mock_update.message.reply_text.assert_called_once_with(MSG_BACKEND_UNAVAILABLE)


@pytest.mark.asyncio
async def test_unknown_command(mock_update, mock_context):
    """Unknown command should reply with standard unknown command message."""
    await _handle_unknown_command(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once_with(MSG_UNKNOWN_COMMAND)


class TestStartCommand:
    """Tests for StartCommand class."""

    def test_name(self):
        """Command name should be 'start'."""
        cmd = StartCommand()
        assert cmd.name == "start"

    def test_description(self):
        """Command should have a description."""
        cmd = StartCommand()
        assert cmd.description != ""


class TestTestCommand:
    """Tests for TestCommand class."""

    def test_name(self):
        """Command name should be 'test'."""
        cmd = TestCommand("project", "region", "service")
        assert cmd.name == "test"

    def test_description(self):
        """Command should have a description."""
        cmd = TestCommand("project", "region", "service")
        assert cmd.description != ""
