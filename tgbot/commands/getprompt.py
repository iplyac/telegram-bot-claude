"""Get prompt command handler."""

import logging
import httpx
from telegram import Update
from telegram.ext import ContextTypes

from .base import BaseCommand
from tgbot.services.backend_client import BackendClient

logger = logging.getLogger(__name__)

# Max prompt length to display (leave room for formatting within Telegram's 4096 limit)
MAX_PROMPT_DISPLAY_LENGTH = 4000


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

        # Call master-agent endpoint
        url = f"{self._backend_client.agent_api_url.rstrip('/')}/api/prompt"
        auth_headers = self._backend_client._get_auth_headers()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=auth_headers)
                response.raise_for_status()
                data = response.json()

            prompt = data.get("prompt", "")
            length = data.get("length", len(prompt))

            # Truncate if needed
            if len(prompt) > MAX_PROMPT_DISPLAY_LENGTH:
                prompt = prompt[:MAX_PROMPT_DISPLAY_LENGTH] + "..."
                header = f"Current prompt ({length} characters, truncated):"
            else:
                header = f"Current prompt ({length} characters):"

            # Format response with code block
            await update.message.reply_text(f"{header}\n\n```\n{prompt}\n```")

        except httpx.HTTPError as e:
            logger.warning(
                f"Get prompt request failed: {type(e).__name__}",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                },
            )
            await update.message.reply_text(f"Failed to get prompt: {e}")
