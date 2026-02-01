"""Voice message handler."""

import base64
import logging
import time

from telegram import Update
from telegram.ext import ContextTypes

from tgbot.logging_config import generate_request_id
from tgbot.services.backend_client import BackendClient, TelegramMetadata

logger = logging.getLogger(__name__)

# Standard user messages (same as text handler)
MSG_AGENT_NOT_CONFIGURED = "AGENT_API_URL is not configured"
MSG_BACKEND_UNAVAILABLE = "Backend unavailable, please try again later."


def _derive_conversation_id(update: Update) -> tuple[str, TelegramMetadata]:
    """
    Derive conversation_id and metadata from Telegram update.

    Returns:
        Tuple of (conversation_id, TelegramMetadata)
    """
    chat = update.effective_chat
    user = update.effective_user

    chat_id = chat.id if chat else 0
    user_id = user.id if user else 0
    chat_type = chat.type if chat else "unknown"

    # Derive conversation_id based on chat type
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


async def handle_voice_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    backend_client: BackendClient,
) -> None:
    """
    Handle incoming voice messages:
    1. Download voice file from Telegram
    2. Base64-encode the audio
    3. Forward to AI Agent /api/voice
    4. Reply with agent response
    """
    if update.effective_user is None or update.message is None:
        return

    voice = update.message.voice
    if voice is None:
        return

    start_time = time.monotonic()
    request_id = generate_request_id()

    # Derive conversation_id and metadata
    conversation_id, metadata = _derive_conversation_id(update)

    logger.info(
        "Message received",
        extra={
            "request_id": request_id,
            "conversation_id": conversation_id,
            "user_id": metadata.user_id,
            "chat_type": metadata.chat_type,
            "update_id": update.update_id,
            "message_type": "voice",
            "audio_duration_seconds": voice.duration,
        },
    )

    # Check if backend is configured
    if backend_client.agent_api_url is None:
        logger.warning(
            "AGENT_API_URL not configured, cannot forward voice",
            extra={"request_id": request_id, "conversation_id": conversation_id},
        )
        await update.message.reply_text(MSG_AGENT_NOT_CONFIGURED)
        return

    try:
        # 1. Download voice file from Telegram
        voice_file = await context.bot.get_file(voice.file_id)
        audio_bytes = await voice_file.download_as_bytearray()

        logger.info(
            "Voice file downloaded",
            extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "size_bytes": len(audio_bytes),
            },
        )

        # 2. Base64-encode
        audio_base64 = base64.b64encode(bytes(audio_bytes)).decode("utf-8")
        mime_type = voice.mime_type or "audio/ogg"

        # 3. Forward to agent
        result = await backend_client.forward_voice(
            conversation_id, audio_base64, mime_type, metadata, request_id
        )

        # 4. Reply to user
        response_text = result.get("response", "")
        if not response_text:
            response_text = "Could not process voice message."

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
                f"Voice forward error: {type(e).__name__}",
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
            f"Voice handler error: {type(e).__name__}",
            extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "user_id": metadata.user_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        await update.message.reply_text(MSG_BACKEND_UNAVAILABLE)
