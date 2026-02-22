"""Session info command handler."""

import logging
import httpx
from telegram import Update
from telegram.ext import ContextTypes

from .base import BaseCommand
from tgbot.services.backend_client import BackendClient

logger = logging.getLogger(__name__)


class SessionInfoCommand(BaseCommand):
    """Handler for the /sessioninfo command."""

    def __init__(self, backend_client: BackendClient):
        self._backend_client = backend_client

    @property
    def name(self) -> str:
        return "sessioninfo"

    @property
    def description(self) -> str:
        return "Show current session information"

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Query and display session information."""
        if update.effective_chat is None or update.message is None:
            return

        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        user_id = update.effective_user.id if update.effective_user else 0

        logger.info(
            "Handling /sessioninfo command",
            extra={"user_id": user_id, "chat_id": chat_id, "chat_type": chat_type},
        )

        # Derive conversation_id — use user_id for private chats (consistent with all handlers)
        if chat_type == "private":
            conversation_id = f"tg_dm_{user_id}"
        elif chat_type in ("group", "supergroup"):
            conversation_id = f"tg_group_{chat_id}"
        else:
            conversation_id = f"tg_chat_{chat_id}"

        # Check if backend is configured
        if self._backend_client.agent_api_url is None:
            await update.message.reply_text(
                "Session info unavailable - backend not configured"
            )
            return

        try:
            data = await self._backend_client.get_session_info(conversation_id)

            # Validate response
            if "session_exists" not in data:
                await update.message.reply_text(
                    "Failed to get session info: invalid response"
                )
                return

            # Format response — no parse_mode to avoid Markdown injection via backend data
            if data.get("session_exists"):
                message_count = data.get("message_count")
                count_str = f"\nMessages: {message_count}" if message_count is not None else ""
                text = (
                    f"Session info:\n"
                    f"- Conversation ID: {data.get('conversation_id', conversation_id)}\n"
                    f"- Session ID: {data.get('session_id', conversation_id)}\n"
                    f"- Status: Active{count_str}"
                )
            else:
                text = (
                    f"No active session for this chat.\n"
                    f"- Conversation ID: {conversation_id}"
                )

            await update.message.reply_text(text)

        except httpx.HTTPError as e:
            logger.warning(
                "Session info request failed",
                extra={
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            await update.message.reply_text("Failed to get session info. Please try again later.")
