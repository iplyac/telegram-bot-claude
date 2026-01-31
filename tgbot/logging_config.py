"""Logging utilities for message flow correlation."""

import uuid


def generate_request_id() -> str:
    """Generate a unique request ID for correlating log entries.

    Returns:
        Request ID in format: req_{8-char-hex}
    """
    return f"req_{uuid.uuid4().hex[:8]}"
