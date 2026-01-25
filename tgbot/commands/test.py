"""Test command handler."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from tgbot.services.diagnostics import get_instance_info

from .base import BaseCommand

logger = logging.getLogger(__name__)


class TestCommand(BaseCommand):
    """Handler for the /test command."""

    def __init__(self, project_id: str, region: str, service_name: str):
        """
        Initialize the test command.

        Args:
            project_id: GCP project ID
            region: Cloud Run region
            service_name: Cloud Run service name
        """
        self._project_id = project_id
        self._region = region
        self._service_name = service_name

    @property
    def name(self) -> str:
        return "test"

    @property
    def description(self) -> str:
        return "Show diagnostic information"

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send diagnostic information."""
        if update.effective_user is None or update.message is None:
            return

        user_id = update.effective_user.id

        logger.info(
            "Handling /test command",
            extra={"user_id": user_id},
        )

        info = get_instance_info(self._project_id, self._region, self._service_name)
        await update.message.reply_text(info)
