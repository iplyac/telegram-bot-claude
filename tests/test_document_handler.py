"""Tests for document message handler."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from tgbot.handlers.document import handle_document_message
from tgbot.services.backend_client import BackendClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_document():
    doc = MagicMock()
    doc.file_id = "doc_file_id"
    doc.mime_type = "application/pdf"
    doc.file_name = "report.pdf"
    doc.file_size = 102400
    return doc


@pytest.fixture
def mock_update(mock_document):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 123456
    update.effective_chat = MagicMock()
    update.effective_chat.id = 123456
    update.effective_chat.type = "private"
    update.message = MagicMock()
    update.message.document = mock_document
    update.message.caption = None
    update.message.reply_text = AsyncMock()
    update.update_id = 987654321
    return update


@pytest.fixture
def mock_context():
    context = MagicMock()
    context.bot = MagicMock()
    mock_file = MagicMock()
    mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake document data"))
    context.bot.get_file = AsyncMock(return_value=mock_file)
    context.bot.send_chat_action = AsyncMock()
    return context


# ---------------------------------------------------------------------------
# BackendClient.forward_document unit tests (task 4.1)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_forward_document_correct_url_and_payload():
    """forward_document posts to /api/document with correct fields."""
    client = BackendClient(agent_api_url="https://example.com")

    captured = {}

    async def fake_post(url, payload, session_id, log_label, request_id="", timeout=None, max_total_time=None, response_field="response"):
        captured["url"] = url
        captured["payload"] = payload
        captured["timeout"] = timeout
        captured["max_total_time"] = max_total_time
        return {"content": "ok"}

    client._post_with_retry = fake_post

    result = await client.forward_document(
        conversation_id="tg_dm_1",
        document_base64="abc123",
        mime_type="application/pdf",
        filename="report.pdf",
        prompt="Summarise this",
        request_id="req-1",
    )

    assert captured["url"] == "https://example.com/api/document"
    assert captured["payload"]["conversation_id"] == "tg_dm_1"
    assert captured["payload"]["document_base64"] == "abc123"
    assert captured["payload"]["mime_type"] == "application/pdf"
    assert captured["payload"]["filename"] == "report.pdf"
    assert captured["payload"]["prompt"] == "Summarise this"
    assert captured["timeout"] == 120.0
    assert captured["max_total_time"] == 180.0
    assert result == {"response": "ok"}  # content normalized to response


@pytest.mark.asyncio
async def test_forward_document_no_prompt_omitted():
    """prompt field is omitted from payload when None."""
    client = BackendClient(agent_api_url="https://example.com")

    captured = {}

    async def fake_post(url, payload, session_id, log_label, request_id="", timeout=None, max_total_time=None, response_field="response"):
        captured["payload"] = payload
        return {"content": "ok"}

    client._post_with_retry = fake_post

    await client.forward_document("tg_dm_1", "abc123", prompt=None)
    assert "prompt" not in captured["payload"]


@pytest.mark.asyncio
async def test_forward_document_raises_if_no_url():
    """forward_document raises ValueError when agent_api_url is None."""
    client = BackendClient(agent_api_url=None)
    with pytest.raises(ValueError, match="AGENT_API_URL is not configured"):
        await client.forward_document("tg_dm_1", "abc123")


# ---------------------------------------------------------------------------
# handle_document_message handler tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_happy_path_pdf(mock_update, mock_context):
    """Happy path: PDF document forwarded, agent response replied."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    with patch.object(
        backend_client,
        "forward_document",
        new_callable=AsyncMock,
        return_value={"response": "This is a summary of the report."},
    ) as mock_forward:
        await handle_document_message(mock_update, mock_context, backend_client)

        mock_forward.assert_called_once()
        args = mock_forward.call_args[0]
        assert args[2] == "application/pdf"   # mime_type
        assert args[3] == "report.pdf"        # filename

        mock_update.message.reply_text.assert_called_once_with(
            "This is a summary of the report."
        )


@pytest.mark.asyncio
async def test_mime_type_fallback(mock_update, mock_context, mock_document):
    """When mime_type is None, fallback to application/octet-stream (task 4.3)."""
    mock_document.mime_type = None
    backend_client = BackendClient(agent_api_url="https://example.com")

    with patch.object(
        backend_client,
        "forward_document",
        new_callable=AsyncMock,
        return_value={"response": "Processed."},
    ) as mock_forward:
        await handle_document_message(mock_update, mock_context, backend_client)

        args = mock_forward.call_args[0]
        assert args[2] == "application/octet-stream"


@pytest.mark.asyncio
async def test_filename_fallback(mock_update, mock_context, mock_document):
    """When file_name is None, fallback to 'document' (task 4.4)."""
    mock_document.file_name = None
    backend_client = BackendClient(agent_api_url="https://example.com")

    with patch.object(
        backend_client,
        "forward_document",
        new_callable=AsyncMock,
        return_value={"response": "Processed."},
    ) as mock_forward:
        await handle_document_message(mock_update, mock_context, backend_client)

        args = mock_forward.call_args[0]
        assert args[3] == "document"


@pytest.mark.asyncio
async def test_agent_url_not_configured(mock_update, mock_context):
    """Should reply with config error when AGENT_API_URL is None (task 4.5)."""
    backend_client = BackendClient(agent_api_url=None)

    await handle_document_message(mock_update, mock_context, backend_client)

    mock_update.message.reply_text.assert_called_once_with(
        "AGENT_API_URL is not configured"
    )
    mock_context.bot.get_file.assert_not_called()


@pytest.mark.asyncio
async def test_backend_error_replies_unavailable(mock_update, mock_context):
    """Should reply with unavailable message on backend exception (task 4.6)."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    with patch.object(
        backend_client,
        "forward_document",
        new_callable=AsyncMock,
        side_effect=Exception("Connection failed"),
    ):
        await handle_document_message(mock_update, mock_context, backend_client)

        mock_update.message.reply_text.assert_called_once_with(
            "Backend unavailable, please try again later."
        )


@pytest.mark.asyncio
async def test_caption_forwarded_as_prompt(mock_update, mock_context):
    """Caption is forwarded as the prompt field."""
    mock_update.message.caption = "Summarise this document"
    backend_client = BackendClient(agent_api_url="https://example.com")

    with patch.object(
        backend_client,
        "forward_document",
        new_callable=AsyncMock,
        return_value={"response": "Summary here."},
    ) as mock_forward:
        await handle_document_message(mock_update, mock_context, backend_client)

        args = mock_forward.call_args[0]
        assert args[4] == "Summarise this document"  # prompt


@pytest.mark.asyncio
async def test_no_caption_prompt_is_none(mock_update, mock_context):
    """No caption means prompt is None (omitted from payload)."""
    mock_update.message.caption = None
    backend_client = BackendClient(agent_api_url="https://example.com")

    with patch.object(
        backend_client,
        "forward_document",
        new_callable=AsyncMock,
        return_value={"response": "Done."},
    ) as mock_forward:
        await handle_document_message(mock_update, mock_context, backend_client)

        args = mock_forward.call_args[0]
        assert args[4] is None  # prompt


@pytest.mark.asyncio
async def test_empty_response_uses_fallback(mock_update, mock_context):
    """Empty response from agent falls back to default message."""
    backend_client = BackendClient(agent_api_url="https://example.com")

    with patch.object(
        backend_client,
        "forward_document",
        new_callable=AsyncMock,
        return_value={"response": ""},
    ):
        await handle_document_message(mock_update, mock_context, backend_client)

        mock_update.message.reply_text.assert_called_once_with(
            "Could not process document."
        )
