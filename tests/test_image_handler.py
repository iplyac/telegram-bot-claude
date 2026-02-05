"""Tests for image/photo message handler."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from tgbot.handlers.image import handle_photo_message, DEFAULT_IMAGE_PROMPT
from tgbot.services.backend_client import BackendClient


@pytest.fixture
def mock_update_with_caption():
    """Create a mock Telegram Update with photo and caption."""
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 123456
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123456
    update.effective_chat.type = "private"
    update.message = MagicMock()
    update.message.caption = "What breed is this dog?"
    update.message.reply_text = AsyncMock()
    update.update_id = 987654321

    # Mock photo list with different sizes
    photo_small = MagicMock()
    photo_small.file_id = "small_file_id"
    photo_small.width = 100
    photo_small.height = 100
    photo_small.file_size = 1000

    photo_large = MagicMock()
    photo_large.file_id = "large_file_id"
    photo_large.width = 800
    photo_large.height = 600
    photo_large.file_size = 50000

    update.message.photo = [photo_small, photo_large]
    return update


@pytest.fixture
def mock_update_no_caption():
    """Create a mock Telegram Update with photo but no caption."""
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 123456
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123456
    update.effective_chat.type = "private"
    update.message = MagicMock()
    update.message.caption = None
    update.message.reply_text = AsyncMock()
    update.update_id = 987654321

    photo = MagicMock()
    photo.file_id = "file_id"
    photo.width = 800
    photo.height = 600
    photo.file_size = 50000

    update.message.photo = [photo]
    return update


@pytest.fixture
def mock_context():
    """Create a mock bot context."""
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.get_file = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_photo_with_caption(mock_update_with_caption, mock_context):
    """Photo with caption should use caption as prompt."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    # Mock file download
    mock_file = MagicMock()
    mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake image data"))
    mock_context.bot.get_file.return_value = mock_file

    with patch.object(
        backend_client,
        "forward_image",
        new_callable=AsyncMock,
        return_value={"response": "This is a Golden Retriever."},
    ) as mock_forward:
        await handle_photo_message(mock_update_with_caption, mock_context, backend_client)

        # Verify forward_image was called with caption as prompt
        mock_forward.assert_called_once()
        call_kwargs = mock_forward.call_args
        assert call_kwargs[0][3] == "What breed is this dog?"  # prompt argument

        # Verify reply
        mock_update_with_caption.message.reply_text.assert_called_once_with(
            "This is a Golden Retriever."
        )


@pytest.mark.asyncio
async def test_photo_without_caption(mock_update_no_caption, mock_context):
    """Photo without caption should use default prompt."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    # Mock file download
    mock_file = MagicMock()
    mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake image data"))
    mock_context.bot.get_file.return_value = mock_file

    with patch.object(
        backend_client,
        "forward_image",
        new_callable=AsyncMock,
        return_value={"response": "This image shows a sunset."},
    ) as mock_forward:
        await handle_photo_message(mock_update_no_caption, mock_context, backend_client)

        # Verify forward_image was called with default prompt
        mock_forward.assert_called_once()
        call_kwargs = mock_forward.call_args
        assert call_kwargs[0][3] == DEFAULT_IMAGE_PROMPT  # prompt argument


@pytest.mark.asyncio
async def test_photo_uses_largest_size(mock_update_with_caption, mock_context):
    """Handler should download the largest photo size."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    # Mock file download
    mock_file = MagicMock()
    mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake image data"))
    mock_context.bot.get_file.return_value = mock_file

    with patch.object(
        backend_client,
        "forward_image",
        new_callable=AsyncMock,
        return_value={"response": "Image analyzed."},
    ):
        await handle_photo_message(mock_update_with_caption, mock_context, backend_client)

        # Verify get_file was called with the largest photo's file_id
        mock_context.bot.get_file.assert_called_once_with("large_file_id")


@pytest.mark.asyncio
async def test_backend_not_configured(mock_update_with_caption, mock_context):
    """Should reply with error when backend not configured."""
    backend_client = BackendClient(agent_api_url=None)

    await handle_photo_message(mock_update_with_caption, mock_context, backend_client)

    mock_update_with_caption.message.reply_text.assert_called_once_with(
        "AGENT_API_URL is not configured"
    )


@pytest.mark.asyncio
async def test_backend_error(mock_update_with_caption, mock_context):
    """Should reply with error on backend failure."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    # Mock file download
    mock_file = MagicMock()
    mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake image data"))
    mock_context.bot.get_file.return_value = mock_file

    with patch.object(
        backend_client,
        "forward_image",
        new_callable=AsyncMock,
        side_effect=Exception("Connection failed"),
    ):
        await handle_photo_message(mock_update_with_caption, mock_context, backend_client)

        mock_update_with_caption.message.reply_text.assert_called_once_with(
            "Backend unavailable, please try again later."
        )


@pytest.mark.asyncio
async def test_download_failure(mock_update_with_caption, mock_context):
    """Should reply with error when photo download fails."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    # Mock file download to fail
    mock_context.bot.get_file.side_effect = Exception("Download failed")

    await handle_photo_message(mock_update_with_caption, mock_context, backend_client)

    mock_update_with_caption.message.reply_text.assert_called_once_with(
        "Backend unavailable, please try again later."
    )
