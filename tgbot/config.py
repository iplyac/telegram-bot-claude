"""Configuration module with stateless functions for retrieving config values."""

import hashlib
import os
from typing import Optional

from secret_manager import get_bot_token_from_secret_manager, extract_bot_token


def sanitize_value(value: Optional[str]) -> Optional[str]:
    """
    Sanitize a configuration value by stripping whitespace and removing control characters.

    Args:
        value: Raw configuration value

    Returns:
        Sanitized value, or None if input was None/empty
    """
    if not value:
        return value
    value = value.strip()
    # Remove control characters (ASCII 0-31 and 127)
    value = "".join(c for c in value if ord(c) > 31 and ord(c) != 127)
    return value if value else None


def get_port() -> int:
    """Get the server port from PORT env var, defaulting to 8080."""
    return int(os.getenv("PORT", "8080"))


def get_project_id() -> str:
    """Get GCP project ID from GCP_PROJECT_ID or PROJECT_ID env vars."""
    return os.getenv("GCP_PROJECT_ID") or os.getenv("PROJECT_ID") or ""


def get_bot_token() -> str:
    """
    Get Telegram bot token following the resolution order:
    1. TELEGRAM_BOT_TOKEN env var
    2. Secret Manager (using TELEGRAM_BOT_TOKEN_SECRET_ID or default "TELEGRAM_BOT_TOKEN")

    Returns:
        Sanitized bot token

    Raises:
        ValueError: If token cannot be resolved from any source
    """
    # Try environment variable first
    token_env = os.getenv("TELEGRAM_BOT_TOKEN")
    if token_env:
        # Extract token in case env var contains multi-line or concatenated format
        token = extract_bot_token(token_env)
        if token:
            sanitized = sanitize_value(token)
            if sanitized:
                return sanitized

    # Try Secret Manager
    project_id = get_project_id()
    secret_id = os.getenv("TELEGRAM_BOT_TOKEN_SECRET_ID", "TELEGRAM_BOT_TOKEN")

    token = get_bot_token_from_secret_manager(project_id, secret_id)
    if token:
        sanitized = sanitize_value(token)
        if sanitized:
            return sanitized

    raise ValueError("TELEGRAM_BOT_TOKEN not found")


def get_agent_api_url() -> Optional[str]:
    """
    Get AGENT_API_URL with sanitization.

    Returns:
        Agent API URL, or None if not configured.
    """
    return sanitize_value(os.getenv("AGENT_API_URL"))


def get_webhook_url() -> Optional[str]:
    """Get TELEGRAM_WEBHOOK_URL with sanitization. Returns None if not configured."""
    return sanitize_value(os.getenv("TELEGRAM_WEBHOOK_URL"))


def get_webhook_path() -> str:
    """Get TELEGRAM_WEBHOOK_PATH, defaulting to /telegram/webhook."""
    path = os.getenv("TELEGRAM_WEBHOOK_PATH", "/telegram/webhook")
    return path if path else "/telegram/webhook"


def get_full_webhook_url() -> Optional[str]:
    """
    Get full webhook URL by combining base URL and path.

    Returns:
        Full webhook URL (e.g., "https://example.com/telegram/webhook"),
        or None if webhook URL is not configured.
    """
    webhook_url = get_webhook_url()
    if not webhook_url:
        return None

    webhook_path = get_webhook_path()
    return webhook_url.rstrip("/") + webhook_path


def get_webhook_secret() -> str:
    """
    Get webhook secret following the resolution order:
    1. TELEGRAM_WEBHOOK_SECRET env var
    2. Derived from bot token (sha256, first 32 hex chars)

    Returns:
        Sanitized webhook secret

    Raises:
        ValueError: If bot token is missing (needed for derivation)
    """
    # Try environment variable first
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if secret:
        sanitized = sanitize_value(secret)
        if sanitized:
            return sanitized

    # Derive from bot token
    bot_token = get_bot_token()
    derived = hashlib.sha256(bot_token.encode()).hexdigest()[:32]
    return derived


def get_log_level() -> str:
    """Get LOG_LEVEL, defaulting to INFO."""
    return os.getenv("LOG_LEVEL", "INFO")


def get_region() -> str:
    """Get REGION, defaulting to europe-west4."""
    return os.getenv("REGION", "europe-west4")


def get_service_name() -> str:
    """Get SERVICE_NAME, defaulting to telegram-bot."""
    return os.getenv("SERVICE_NAME", "telegram-bot")
