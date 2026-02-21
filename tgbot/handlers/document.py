"""Document message handler."""

import base64
import logging
import time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from tgbot.logging_config import generate_request_id
from tgbot.services.backend_client import BackendClient, TelegramMetadata

logger = logging.getLogger(__name__)

MSG_AGENT_NOT_CONFIGURED = "AGENT_API_URL is not configured"
MSG_BACKEND_UNAVAILABLE = "Backend unavailable, please try again later."


def _derive_conversation_id(update: Update) -> tuple[str, TelegramMetadata]:
    """Derive conversation_id and metadata from Telegram update."""
    chat = update.effective_chat
    user = update.effective_user

    chat_id = chat.id if chat else 0
    user_id = user.id if user else 0
    chat_type = chat.type if chat else "unknown"

    if chat_type == "private":
        conversation_id = f"tg_dm_{user_id}"
    elif chat_type in ("group", "supergroup"):
        conversation_id = f"tg_group_{chat_id}"
    else:
        conversation_id = f"tg_chat_{chat_id}"

    metadata = TelegramMetadata(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=chat_type,
    )

    return conversation_id, metadata


async def handle_document_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    backend_client: BackendClient,
) -> None:
    """
    Handle incoming document messages:
    1. Download document from Telegram
    2. Base64-encode the document
    3. Forward to AI Agent /api/document
    4. Reply with agent response
    """
    if update.effective_user is None or update.message is None:
        return

    document = update.message.document
    if not document:
        return

    start_time = time.monotonic()
    request_id = generate_request_id()

    conversation_id, metadata = _derive_conversation_id(update)

    # Derive MIME type — fallback to octet-stream if Telegram doesn't provide one
    mime_type = document.mime_type or "application/octet-stream"

    # Derive filename — fallback to "document" if not provided
    filename = document.file_name or "document"

    logger.info(
        "Message received",
        extra={
            "request_id": request_id,
            "conversation_id": conversation_id,
            "user_id": metadata.user_id,
            "chat_type": metadata.chat_type,
            "update_id": update.update_id,
            "message_type": "document",
            "mime_type": mime_type,
            "doc_filename": filename,
            "file_size": document.file_size,
        },
    )

    if backend_client.agent_api_url is None:
        logger.warning(
            "AGENT_API_URL not configured, cannot forward document",
            extra={"request_id": request_id, "conversation_id": conversation_id},
        )
        await update.message.reply_text(MSG_AGENT_NOT_CONFIGURED)
        return

    try:
        # Download document from Telegram
        doc_file = await context.bot.get_file(document.file_id)
        doc_bytes = await doc_file.download_as_bytearray()

        logger.info(
            "Document file downloaded",
            extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "size_bytes": len(doc_bytes),
            },
        )

        # Base64-encode
        document_base64 = base64.b64encode(bytes(doc_bytes)).decode("utf-8")

        # Use caption as prompt if present
        prompt = update.message.caption or None

        # Send typing indicator while waiting for agent
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action=ChatAction.TYPING
        )

        # Forward to agent
        result = await backend_client.forward_document(
            conversation_id,
            document_base64,
            mime_type,
            filename,
            prompt,
            metadata,
            request_id,
        )

        # Reply to user
        response_text = result.get("response", "")
        if not response_text:
            response_text = "Could not process document."

        await update.message.reply_text(response_text)

        latency_total_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            "Reply sent",
            extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "user_id": metadata.user_id,
                "latency_total_ms": latency_total_ms,
            },
        )

    except ValueError as e:
        error_str = str(e)
        if "AGENT_API_URL is not configured" in error_str:
            await update.message.reply_text(MSG_AGENT_NOT_CONFIGURED)
        else:
            logger.error(
                f"Document forward error: {type(e).__name__}",
                extra={
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "user_id": metadata.user_id,
                    "error_type": type(e).__name__,
                    "error_message": error_str,
                },
            )
            await update.message.reply_text(MSG_BACKEND_UNAVAILABLE)

    except Exception as e:
        logger.error(
            f"Document handler error: {type(e).__name__}",
            extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "user_id": metadata.user_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        await update.message.reply_text(MSG_BACKEND_UNAVAILABLE)
