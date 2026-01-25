"""Base class for bot commands."""

from abc import ABC, abstractmethod

from telegram import Update
from telegram.ext import ContextTypes


class BaseCommand(ABC):
    """Abstract base class for all bot commands."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Command name without the leading slash."""
        pass

    @property
    def description(self) -> str:
        """Command description for help text."""
        return ""

    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the command.

        Args:
            update: Telegram update object
            context: Bot context
        """
        pass
