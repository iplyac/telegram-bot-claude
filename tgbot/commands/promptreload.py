"""Prompt reload command handler."""

import logging
from typing import Optional

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from .base import BaseCommand

logger = logging.getLogger(__name__)


class PromptReloadCommand(BaseCommand):
    """Handler for the /promptreload command."""

    def __init__(self, agent_api_url: Optional[str]):
        """
        Initialize the prompt reload command.

        Args:
            agent_api_url: Base URL for the agent API, or None if not configured
        """
        self._agent_api_url = agent_api_url

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

        logger.info(
            "Handling /promptreload command",
            extra={"user_id": user_id},
        )

        # Check if backend is configured
        if self._agent_api_url is None:
            await update.message.reply_text(
                "Prompt reload unavailable - backend not configured"
            )
            return

        # Call master-agent endpoint
        url = f"{self._agent_api_url.rstrip('/')}/api/reload-prompt"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url)
                response.raise_for_status()
                data = response.json()

            # Handle response
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
                f"Prompt reload request failed: {type(e).__name__}",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                },
            )
            await update.message.reply_text(f"Failed to reload prompt: {e}")
