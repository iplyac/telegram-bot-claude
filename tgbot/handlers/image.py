"""Image/photo message handler."""

import base64
import io
import logging
import time

from telegram import InputFile, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from tgbot.logging_config import generate_request_id
from tgbot.utils import derive_conversation_id
from tgbot.services.backend_client import BackendClient

logger = logging.getLogger(__name__)

# Standard user messages (same as text handler)
MSG_AGENT_NOT_CONFIGURED = "AGENT_API_URL is not configured"
MSG_BACKEND_UNAVAILABLE = "Backend unavailable, please try again later."

# Default prompt when no caption provided
DEFAULT_IMAGE_PROMPT = "What is in this image?"

# Mapping MIME types to file extensions for Telegram
MIME_TO_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}

MAX_PHOTO_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB — Telegram bot API limit


async def handle_photo_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    backend_client: BackendClient,
) -> None:
    """
    Handle incoming photo messages:
    1. Download photo from Telegram (largest size)
    2. Base64-encode the image
    3. Forward to AI Agent /api/image
    4. Reply with agent response
    """
    if update.effective_user is None or update.message is None:
        return

    photo_list = update.message.photo
    if not photo_list:
        return

    start_time = time.monotonic()
    request_id = generate_request_id()

    # Derive conversation_id and metadata
    conversation_id, metadata = derive_conversation_id(update)

    # Get largest photo size
    photo = photo_list[-1]

    # Reject oversized files early to avoid wasting memory and bandwidth
    if photo.file_size and photo.file_size > MAX_PHOTO_SIZE_BYTES:
        await update.message.reply_text("Photo too large (max 20 MB).")
        return

    logger.info(
        "Message received",
        extra={
            "request_id": request_id,
            "conversation_id": conversation_id,
            "user_id": metadata.user_id,
            "chat_type": metadata.chat_type,
            "update_id": update.update_id,
            "message_type": "photo",
            "photo_width": photo.width,
            "photo_height": photo.height,
            "photo_file_size": photo.file_size,
        },
    )

    # Check if backend is configured
    if backend_client.agent_api_url is None:
        logger.warning(
            "AGENT_API_URL not configured, cannot forward photo",
            extra={"request_id": request_id, "conversation_id": conversation_id},
        )
        await update.message.reply_text(MSG_AGENT_NOT_CONFIGURED)
        return

    try:
        # 1. Download photo from Telegram
        photo_file = await context.bot.get_file(photo.file_id)
        image_bytes = await photo_file.download_as_bytearray()

        logger.info(
            "Photo file downloaded",
            extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "size_bytes": len(image_bytes),
            },
        )

        # 2. Base64-encode
        image_base64 = base64.b64encode(bytes(image_bytes)).decode("utf-8")

        # 3. Determine MIME type (Telegram photos are typically JPEG)
        mime_type = "image/jpeg"

        # 4. Use caption as prompt or default
        prompt = update.message.caption or DEFAULT_IMAGE_PROMPT

        # 5. Send typing indicator while waiting for agent
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action=ChatAction.TYPING
        )

        # 6. Forward to agent
        result = await backend_client.forward_image(
            conversation_id, image_base64, mime_type, prompt, metadata, request_id
        )

        # 6. Reply to user
        response_text = result.get("response", "")
        if not response_text:
            response_text = "Could not process image."

        # Check if agent returned a processed image
        processed_image_b64 = result.get("processed_image_base64")
        processed_mime = result.get("processed_image_mime_type")

        if processed_image_b64 and processed_mime:
            image_bytes = base64.b64decode(processed_image_b64)
            ext = MIME_TO_EXT.get(processed_mime, "png")
            await update.message.reply_photo(
                photo=InputFile(io.BytesIO(image_bytes), filename=f"processed.{ext}"),
                caption=response_text[:1024] if response_text else None,
            )
        else:
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
                f"Image forward error: {type(e).__name__}",
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
            f"Image handler error: {type(e).__name__}",
            extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "user_id": metadata.user_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        await update.message.reply_text(MSG_BACKEND_UNAVAILABLE)
