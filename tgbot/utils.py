"""Shared utilities for handler modules."""

from telegram import Update

from tgbot.services.backend_client import TelegramMetadata


def derive_conversation_id(update: Update) -> tuple[str, TelegramMetadata]:
    """
    Derive conversation_id and metadata from a Telegram update.

    Conversation ID format:
        - Private chat: tg_dm_{user_id}
        - Group/Supergroup: tg_group_{chat_id}
        - Unknown: tg_chat_{chat_id}

    Returns:
        Tuple of (conversation_id, TelegramMetadata)
    """
    chat = update.effective_chat
    user = update.effective_user

    chat_id = chat.id if chat else 0
    user_id = user.id if user else 0
    chat_type = chat.type if chat else "unknown"

    if chat_type == "private":
        conversation_id = f"tg_dm_{user_id}"
    elif chat_type in ("group", "supergroup"):
        conversation_id = f"tg_group_{chat_id}"
    else:
        conversation_id = f"tg_chat_{chat_id}"

    metadata = TelegramMetadata(
        chat_id=chat_id,
        user_id=user_id,
        chat_type=chat_type,
    )

    return conversation_id, metadata
