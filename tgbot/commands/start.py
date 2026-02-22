"""Start command handler."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from .base import BaseCommand

logger = logging.getLogger(__name__)


class StartCommand(BaseCommand):
    """Handler for the /start command."""

    @property
    def name(self) -> str:
        return "start"

    @property
    def description(self) -> str:
        return "Start the bot and get a greeting"

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a greeting message."""
        if update.effective_user is None or update.message is None:
            return

        user_id = update.effective_user.id
        first_name = update.effective_user.first_name or "there"

        logger.info(
            "Handling /start command",
            extra={"user_id": user_id},
        )

        greeting = (
            f"Hello, {first_name}! Welcome to the bot.\n\n"
            "I can forward your messages to the backend service.\n"
            "Just send me a text message, photo, voice message, or document to get started.\n\n"
            "Commands:\n"
            "/start - Show this greeting\n"
            "/test - Show diagnostic information\n"
            "/sessioninfo - Show current session info\n"
            "/promptreload - Reload the AI agent system prompt\n"
            "/getprompt - Display the current AI agent system prompt"
        )

        await update.message.reply_text(greeting)
