"""Voice message handler."""

import base64
import logging

from telegram import Update
from telegram.ext import ContextTypes

from tgbot.services.backend_client import BackendClient

logger = logging.getLogger(__name__)

# Standard user messages (same as text handler)
MSG_AGENT_NOT_CONFIGURED = "AGENT_API_URL is not configured"
MSG_BACKEND_UNAVAILABLE = "Backend unavailable, please try again later."


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

    user_id = update.effective_user.id
    session_id = f"tg_{user_id}"

    logger.info(
        "Voice message received",
        extra={
            "user_id": user_id,
            "session_id": session_id,
            "duration": voice.duration,
            "file_size": voice.file_size,
            "mime_type": voice.mime_type,
            "update_id": update.update_id,
        },
    )

    # Check if backend is configured
    if backend_client.agent_api_url is None:
        logger.warning(
            "AGENT_API_URL not configured, cannot forward voice",
            extra={"user_id": user_id},
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
                "session_id": session_id,
                "size_bytes": len(audio_bytes),
            },
        )

        # 2. Base64-encode
        audio_base64 = base64.b64encode(bytes(audio_bytes)).decode("utf-8")
        mime_type = voice.mime_type or "audio/ogg"

        # 3. Forward to agent
        result = await backend_client.forward_voice(session_id, audio_base64, mime_type)

        # 4. Reply to user
        response_text = result.get("response", "")
        if not response_text:
            response_text = "Could not process voice message."

        await update.message.reply_text(response_text)

    except ValueError as e:
        error_str = str(e)
        if "AGENT_API_URL is not configured" in error_str:
            await update.message.reply_text(MSG_AGENT_NOT_CONFIGURED)
        else:
            logger.error(
                f"Voice forward error: {type(e).__name__}",
                extra={"user_id": user_id, "error": error_str},
            )
            await update.message.reply_text(MSG_BACKEND_UNAVAILABLE)

    except Exception as e:
        logger.error(
            f"Voice handler error: {type(e).__name__}",
            extra={"user_id": user_id, "error": str(e)},
        )
        await update.message.reply_text(MSG_BACKEND_UNAVAILABLE)
