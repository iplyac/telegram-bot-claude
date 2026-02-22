"""Dispatcher module for registering handlers on the Telegram application."""

import logging
import time
from typing import Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from tgbot.commands.start import StartCommand
from tgbot.commands.test import TestCommand
from tgbot.commands.sessioninfo import SessionInfoCommand
from tgbot.commands.promptreload import PromptReloadCommand
from tgbot.commands.getprompt import GetPromptCommand
from tgbot.commands.status import status_command
from tgbot.handlers.voice import handle_voice_message
from tgbot.handlers.image import handle_photo_message
from tgbot.handlers.document import handle_document_message
from tgbot.logging_config import generate_request_id
from tgbot.services.backend_client import BackendClient, TelegramMetadata
from tgbot.utils import derive_conversation_id as _derive_conversation_id

logger = logging.getLogger(__name__)

# Standard user messages (verbatim from spec)
MSG_AGENT_NOT_CONFIGURED = "AGENT_API_URL is not configured"
MSG_BACKEND_UNAVAILABLE = "Backend unavailable, please try again later."
MSG_UNKNOWN_COMMAND = "Unknown command. Use /start for help."


# Re-export for backwards compatibility with existing imports and tests
derive_conversation_id = _derive_conversation_id


def setup_handlers(
    application: Application,
    backend_client: BackendClient,
    project_id: str,
    region: str,
    service_name: str,
) -> None:
    """
    Register all handlers on the Telegram application.

    Args:
        application: Telegram bot Application instance
        backend_client: BackendClient for forwarding messages
        project_id: GCP project ID
        region: Cloud Run region
        service_name: Cloud Run service name
    """
    # Create command instances
    start_cmd = StartCommand()
    test_cmd = TestCommand(project_id, region, service_name)
    sessioninfo_cmd = SessionInfoCommand(backend_client)
    promptreload_cmd = PromptReloadCommand(backend_client)
    getprompt_cmd = GetPromptCommand(backend_client)

    # Register command handlers
    application.add_handler(CommandHandler(start_cmd.name, start_cmd.handle))
    application.add_handler(CommandHandler(test_cmd.name, test_cmd.handle))
    application.add_handler(CommandHandler(sessioninfo_cmd.name, sessioninfo_cmd.handle))
    application.add_handler(CommandHandler(promptreload_cmd.name, promptreload_cmd.handle))
    application.add_handler(CommandHandler(getprompt_cmd.name, getprompt_cmd.handle))
    application.add_handler(CommandHandler("status", status_command))

    # Create message handler with closure over backend_client
    async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _handle_text_message(update, context, backend_client)

    # Register text message handler (non-command text messages)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )

    # Create voice handler with closure over backend_client
    async def _voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await handle_voice_message(update, context, backend_client)

    # Register voice message handler (after text, before unknown command)
    application.add_handler(
        MessageHandler(filters.VOICE, _voice_handler)
    )

    # Create photo handler with closure over backend_client
    async def _photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await handle_photo_message(update, context, backend_client)

    # Register photo message handler
    application.add_handler(
        MessageHandler(filters.PHOTO, _photo_handler)
    )

    # Create document handler with closure over backend_client
    async def _document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await handle_document_message(update, context, backend_client)

    # Register document message handler (after photo, before unknown command)
    application.add_handler(
        MessageHandler(filters.Document.ALL, _document_handler)
    )

    # Register unknown command handler
    application.add_handler(
        MessageHandler(filters.COMMAND, _handle_unknown_command)
    )

    logger.info("All handlers registered successfully")


async def _handle_text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    backend_client: BackendClient,
) -> None:
    """
    Handle incoming text messages by forwarding to backend.

    Args:
        update: Telegram update object
        context: Bot context
        backend_client: BackendClient instance
    """
    if update.effective_user is None or update.message is None or update.message.text is None:
        return

    start_time = time.monotonic()
    request_id = generate_request_id()
    message_text = update.message.text

    # Derive conversation_id and metadata
    conversation_id, metadata = derive_conversation_id(update)

    logger.info(
        "Message received",
        extra={
            "request_id": request_id,
            "conversation_id": conversation_id,
            "user_id": metadata.user_id,
            "chat_type": metadata.chat_type,
            "update_id": update.update_id,
            "message_type": "text",
            "message_length": len(message_text),
        },
    )

    # Check if backend is configured
    if backend_client.agent_api_url is None:
        logger.warning(
            "AGENT_API_URL not configured, cannot forward message",
            extra={"request_id": request_id, "conversation_id": conversation_id},
        )
        await update.message.reply_text(MSG_AGENT_NOT_CONFIGURED)
        return

    # Forward to backend
    try:
        response = await backend_client.forward_message(
            conversation_id, message_text, metadata, request_id
        )
        await update.message.reply_text(response)

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
    except Exception as e:
        logger.error(
            f"Backend error: {type(e).__name__}",
            extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "user_id": metadata.user_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        await update.message.reply_text(MSG_BACKEND_UNAVAILABLE)


async def _handle_unknown_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle unknown commands."""
    if update.effective_user is None or update.message is None:
        return

    logger.info(
        "Unknown command received",
        extra={
            "user_id": update.effective_user.id,
            "update_id": update.update_id,
        },
    )

    await update.message.reply_text(MSG_UNKNOWN_COMMAND)
