"""Prompt reload command handler."""

import logging
import httpx
from telegram import Update
from telegram.ext import ContextTypes

from .base import BaseCommand
from tgbot import config
from tgbot.services.backend_client import BackendClient

logger = logging.getLogger(__name__)

# Admin user IDs — loaded once at import time from ADMIN_USER_IDS env var.
# If empty, the command is unrestricted (not recommended for production).
_ADMIN_USER_IDS = config.get_admin_user_ids()


class PromptReloadCommand(BaseCommand):
    """Handler for the /promptreload command."""

    def __init__(self, backend_client: BackendClient):
        self._backend_client = backend_client

    @property
    def name(self) -> str:
        return "promptreload"

    @property
    def description(self) -> str:
        return "Reload the AI agent system prompt"

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Trigger prompt reload on master-agent."""
        if update.effective_user is None or update.message is None:
            return

        user_id = update.effective_user.id

        # Access control — only allowed user IDs may reload the prompt
        if _ADMIN_USER_IDS and user_id not in _ADMIN_USER_IDS:
            logger.warning(
                "Unauthorized /promptreload attempt",
                extra={"user_id": user_id},
            )
            await update.message.reply_text("Unauthorized.")
            return

        logger.info(
            "Handling /promptreload command",
            extra={"user_id": user_id},
        )

        # Check if backend is configured
        if self._backend_client.agent_api_url is None:
            await update.message.reply_text(
                "Prompt reload unavailable - backend not configured"
            )
            return

        try:
            data = await self._backend_client.reload_prompt()

            status = data.get("status")

            if status == "ok":
                prompt_length = data.get("prompt_length", "unknown")
                await update.message.reply_text(
                    f"Prompt reloaded successfully ({prompt_length} characters)"
                )
            elif status == "error":
                error_msg = data.get("error", "Unknown error")
                await update.message.reply_text(
                    f"Failed to reload prompt: {error_msg}"
                )
            else:
                await update.message.reply_text(
                    "Failed to reload prompt: unexpected response"
                )

        except httpx.HTTPError as e:
            logger.warning(
                "Prompt reload request failed",
                extra={
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            await update.message.reply_text("Failed to reload prompt. Please try again later.")
