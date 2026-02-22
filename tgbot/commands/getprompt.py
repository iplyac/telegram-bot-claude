"""Get prompt command handler."""

import logging
import httpx
from telegram import Update
from telegram.ext import ContextTypes

from .base import BaseCommand
from tgbot import config
from tgbot.services.backend_client import BackendClient

logger = logging.getLogger(__name__)

# Max prompt length to display (leave room for formatting within Telegram's 4096 limit)
MAX_PROMPT_DISPLAY_LENGTH = 4000

# Admin user IDs — loaded once at import time from ADMIN_USER_IDS env var.
# If empty, the command is unrestricted (not recommended for production).
_ADMIN_USER_IDS = config.get_admin_user_ids()


class GetPromptCommand(BaseCommand):
    """Handler for the /getprompt command."""

    def __init__(self, backend_client: BackendClient):
        self._backend_client = backend_client

    @property
    def name(self) -> str:
        return "getprompt"

    @property
    def description(self) -> str:
        return "Get the current AI agent system prompt"

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Retrieve and display the current system prompt."""
        if update.effective_user is None or update.message is None:
            return

        user_id = update.effective_user.id

        # Access control — only allowed user IDs may view the system prompt
        if _ADMIN_USER_IDS and user_id not in _ADMIN_USER_IDS:
            logger.warning(
                "Unauthorized /getprompt attempt",
                extra={"user_id": user_id},
            )
            await update.message.reply_text("Unauthorized.")
            return

        logger.info(
            "Handling /getprompt command",
            extra={"user_id": user_id},
        )

        # Check if backend is configured
        if self._backend_client.agent_api_url is None:
            await update.message.reply_text(
                "Get prompt unavailable - backend not configured"
            )
            return

        try:
            data = await self._backend_client.get_prompt()

            prompt = data.get("prompt", "")
            length = data.get("length", len(prompt))

            # Truncate if needed
            if len(prompt) > MAX_PROMPT_DISPLAY_LENGTH:
                prompt = prompt[:MAX_PROMPT_DISPLAY_LENGTH] + "..."
                header = f"Current prompt ({length} characters, truncated):"
            else:
                header = f"Current prompt ({length} characters):"

            # Format response with code block
            await update.message.reply_text(
                f"{header}\n\n```\n{prompt}\n```",
                parse_mode="Markdown",
            )

        except httpx.HTTPError as e:
            logger.warning(
                "Get prompt request failed",
                extra={
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            await update.message.reply_text("Failed to get prompt. Please try again later.")
