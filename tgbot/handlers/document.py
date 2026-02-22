"""Document message handler."""

import base64
import io
import logging
import os
import time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from tgbot.logging_config import generate_request_id
from tgbot.utils import derive_conversation_id
from tgbot.services.backend_client import BackendClient

logger = logging.getLogger(__name__)

MSG_AGENT_NOT_CONFIGURED = "AGENT_API_URL is not configured"
MSG_BACKEND_UNAVAILABLE = "Backend unavailable, please try again later."

MAX_DOC_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB — Telegram bot API limit


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

    # Reject oversized files early to avoid wasting memory and bandwidth
    if document.file_size and document.file_size > MAX_DOC_SIZE_BYTES:
        await update.message.reply_text("Document too large (max 20 MB).")
        return

    start_time = time.monotonic()
    request_id = generate_request_id()

    conversation_id, metadata = derive_conversation_id(update)

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

        # Build processing summary
        meta = result.get("metadata") or {}
        content = result.get("response", "")

        summary_lines = [f"Document processed: {filename}"]
        details = []
        if meta.get("pages") is not None:
            details.append(f"Pages: {meta['pages']}")
        if meta.get("tables_found") is not None:
            details.append(f"Tables: {meta['tables_found']}")
        if meta.get("images_found") is not None:
            details.append(f"Images: {meta['images_found']}")
        if details:
            summary_lines.append(" | ".join(details))
        if meta.get("processing_time_ms") is not None:
            summary_lines.append(f"Processing time: {meta['processing_time_ms'] / 1000:.1f}s")
        ai_summary = result.get("summary")
        if ai_summary:
            summary_lines.append(f"\n{ai_summary}")
        if not content:
            summary_lines.append("No content extracted.")

        await update.message.reply_text("\n".join(summary_lines))

        # Send extracted content as .md attachment
        if content:
            basename = os.path.splitext(filename)[0]
            md_filename = f"{basename}.md"
            md_bytes = io.BytesIO(content.encode("utf-8"))
            md_bytes.name = md_filename
            await update.message.reply_document(
                document=md_bytes,
                filename=md_filename,
            )

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
