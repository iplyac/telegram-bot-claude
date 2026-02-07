"""Tests for voice message handler."""

import base64

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from tgbot.handlers.voice import handle_voice_message, MSG_AGENT_NOT_CONFIGURED, MSG_BACKEND_UNAVAILABLE
from tgbot.services.backend_client import BackendClient


@pytest.fixture
def mock_voice_update():
    """Create a mock Telegram Update with a voice message."""
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 123456
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123456
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    update.update_id = 987654321

    # Voice message attributes
    update.message.voice = MagicMock()
    update.message.voice.file_id = "voice_file_id_123"
    update.message.voice.duration = 5
    update.message.voice.file_size = 12345
    update.message.voice.mime_type = "audio/ogg"

    return update


@pytest.fixture
def mock_context():
    """Create a mock bot context."""
    context = MagicMock()
    # Mock get_file and download
    mock_file = MagicMock()
    mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake_audio_data"))
    context.bot.get_file = AsyncMock(return_value=mock_file)
    context.bot.send_message = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_voice_handler_forwards_to_agent(mock_voice_update, mock_context):
    """Voice handler should download file, base64 encode, forward to agent, and reply."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    expected_response = {"response": "I heard you say hello!", "transcription": "hello"}

    with patch.object(
        backend_client,
        "forward_voice",
        new_callable=AsyncMock,
        return_value=expected_response,
    ):
        await handle_voice_message(mock_voice_update, mock_context, backend_client)

        # Verify file was downloaded
        mock_context.bot.get_file.assert_called_once_with("voice_file_id_123")

        # Verify reply was sent
        mock_voice_update.message.reply_text.assert_called_once_with("I heard you say hello!")


@pytest.mark.asyncio
async def test_voice_handler_no_agent_url(mock_voice_update, mock_context):
    """Voice handler without AGENT_API_URL should reply with configuration error."""
    backend_client = BackendClient(agent_api_url=None)

    await handle_voice_message(mock_voice_update, mock_context, backend_client)

    mock_voice_update.message.reply_text.assert_called_once_with(MSG_AGENT_NOT_CONFIGURED)

    # Should NOT attempt to download file
    mock_context.bot.get_file.assert_not_called()


@pytest.mark.asyncio
async def test_voice_handler_agent_error(mock_voice_update, mock_context):
    """Voice handler should reply with error if agent fails."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    with patch.object(
        backend_client,
        "forward_voice",
        new_callable=AsyncMock,
        side_effect=Exception("Agent connection failed"),
    ):
        await handle_voice_message(mock_voice_update, mock_context, backend_client)

        mock_voice_update.message.reply_text.assert_called_once_with(MSG_BACKEND_UNAVAILABLE)


@pytest.mark.asyncio
async def test_voice_handler_download_error(mock_voice_update, mock_context):
    """Voice handler should reply with error if file download fails."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    # Make get_file raise
    mock_context.bot.get_file = AsyncMock(side_effect=Exception("Download failed"))

    await handle_voice_message(mock_voice_update, mock_context, backend_client)

    mock_voice_update.message.reply_text.assert_called_once_with(MSG_BACKEND_UNAVAILABLE)


@pytest.mark.asyncio
async def test_voice_handler_empty_response(mock_voice_update, mock_context):
    """Voice handler should send fallback text if agent returns empty response."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    with patch.object(
        backend_client,
        "forward_voice",
        new_callable=AsyncMock,
        return_value={"response": "", "transcription": ""},
    ):
        await handle_voice_message(mock_voice_update, mock_context, backend_client)

        mock_voice_update.message.reply_text.assert_called_once_with(
            "Could not process voice message."
        )


@pytest.mark.asyncio
async def test_voice_handler_base64_encoding(mock_voice_update, mock_context):
    """Voice handler should correctly base64 encode the audio bytes."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    test_audio = bytearray(b"test_audio_bytes_123")
    expected_b64 = base64.b64encode(bytes(test_audio)).decode("utf-8")

    # Set up download to return specific bytes
    mock_file = MagicMock()
    mock_file.download_as_bytearray = AsyncMock(return_value=test_audio)
    mock_context.bot.get_file = AsyncMock(return_value=mock_file)

    with patch.object(
        backend_client,
        "forward_voice",
        new_callable=AsyncMock,
        return_value={"response": "ok", "transcription": "test"},
    ) as mock_forward:
        await handle_voice_message(mock_voice_update, mock_context, backend_client)

        # Verify forward_voice was called with correct base64
        call_args = mock_forward.call_args
        assert call_args[0][0] == "tg_chat_123456"  # conversation_id (format: tg_chat_{chat_id})
        assert call_args[0][1] == expected_b64  # audio_base64
        assert call_args[0][2] == "audio/ogg"  # mime_type
