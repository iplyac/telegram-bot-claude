"""Google Secret Manager integration for retrieving secrets."""

import logging
import re
from typing import Optional

from google.cloud import secretmanager

logger = logging.getLogger(__name__)


def get_secret(project_id: str, secret_id: str, version: str = "latest") -> Optional[str]:
    """
    Fetch a secret from Google Secret Manager.

    Args:
        project_id: GCP project ID
        secret_id: Secret name/ID
        version: Secret version (default: "latest")

    Returns:
        Secret value as string, or None if not found
    """
    if not project_id:
        logger.warning("project_id is empty, cannot fetch secret from Secret Manager")
        return None

    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
        response = client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("utf-8")
        return payload
    except Exception as e:
        logger.warning(f"Failed to fetch secret {secret_id}: {type(e).__name__}")
        return None


def extract_bot_token(payload: str) -> Optional[str]:
    """
    Extract TELEGRAM_BOT_TOKEN from a secret payload.

    Handles multiple formats:
    - Single-line: just the token value
    - Multi-line key=value pairs separated by newlines
    - Concatenated key=value pairs without newlines

    Args:
        payload: Raw secret payload string

    Returns:
        Extracted token value, or None if not found
    """
    if not payload:
        return None

    payload = payload.strip()

    # Try to find TELEGRAM_BOT_TOKEN= anywhere in the payload using regex
    # Token format: digits:alphanumeric string (e.g., 1234567890:ABCdefGHI...)
    match = re.search(r'TELEGRAM_BOT_TOKEN=(\d+:[A-Za-z0-9_-]+)', payload)
    if match:
        return match.group(1)

    # Fallback: check multi-line format
    lines = payload.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            token = line[len("TELEGRAM_BOT_TOKEN="):]
            return token.strip() if token else None

    # If no key=value format found, assume single-line format (entire payload is the token)
    if "=" not in payload:
        return payload.strip()

    # Payload has key=value format but no TELEGRAM_BOT_TOKEN key
    return None


def get_bot_token_from_secret_manager(
    project_id: str, secret_id: str = "TELEGRAM_BOT_TOKEN", version: str = "latest"
) -> Optional[str]:
    """
    Fetch and extract bot token from Secret Manager.

    Args:
        project_id: GCP project ID
        secret_id: Secret name/ID (default: "TELEGRAM_BOT_TOKEN")
        version: Secret version (default: "latest")

    Returns:
        Extracted bot token, or None if not found
    """
    payload = get_secret(project_id, secret_id, version)
    if payload is None:
        return None

    token = extract_bot_token(payload)
    if token:
        logger.info(f"Successfully extracted bot token from secret {secret_id}")
    else:
        logger.warning(f"Secret {secret_id} exists but TELEGRAM_BOT_TOKEN not found in payload")

    return token
