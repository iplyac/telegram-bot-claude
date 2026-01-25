"""Backend client service for forwarding messages to the agent API."""

import asyncio
import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Retry configuration
MAX_ATTEMPTS = 3
MAX_TOTAL_TIME = 30.0  # seconds
RETRYABLE_STATUS_CODES = {502, 503, 504}


class BackendClient:
    """Client for communicating with the backend agent API."""

    def __init__(self, agent_api_url: Optional[str]):
        """
        Initialize the backend client.

        Args:
            agent_api_url: Base URL for the agent API, or None if not configured
        """
        self.agent_api_url = agent_api_url
        self._client = httpx.AsyncClient(timeout=30.0)

    async def forward_message(self, session_id: str, message: str) -> str:
        """
        Forward a message to the backend agent API.

        Args:
            session_id: Session identifier (format: "tg_<telegram_user_id>")
            message: User message text

        Returns:
            Response text from the backend

        Raises:
            ValueError: If AGENT_API_URL is not configured or response is invalid
            httpx.HTTPError: If all retry attempts fail
        """
        if self.agent_api_url is None:
            raise ValueError("AGENT_API_URL is not configured")

        url = f"{self.agent_api_url.rstrip('/')}/api/chat"
        payload = {"session_id": session_id, "message": message}

        start_time = time.monotonic()
        last_exception: Optional[Exception] = None

        for attempt in range(MAX_ATTEMPTS):
            # Check if we've exceeded total time budget
            elapsed = time.monotonic() - start_time
            if elapsed >= MAX_TOTAL_TIME:
                logger.warning(
                    f"Retry budget exhausted after {elapsed:.1f}s",
                    extra={"session_id": session_id, "attempts": attempt},
                )
                break

            try:
                logger.info(
                    f"Forwarding message to backend (attempt {attempt + 1}/{MAX_ATTEMPTS})",
                    extra={
                        "session_id": session_id,
                        "message_length": len(message),
                        "attempt": attempt + 1,
                    },
                )

                response = await self._client.post(url, json=payload)
                response.raise_for_status()

                data = response.json()
                if "response" not in data:
                    raise ValueError("Missing 'response' field in backend response")

                logger.info(
                    "Backend response received",
                    extra={
                        "session_id": session_id,
                        "status_code": response.status_code,
                    },
                )
                return data["response"]

            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                last_exception = e
                logger.warning(
                    f"Connection error on attempt {attempt + 1}: {type(e).__name__}",
                    extra={"session_id": session_id, "attempt": attempt + 1},
                )

            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code in RETRYABLE_STATUS_CODES:
                    logger.warning(
                        f"Retryable HTTP error {e.response.status_code} on attempt {attempt + 1}",
                        extra={
                            "session_id": session_id,
                            "status_code": e.response.status_code,
                            "attempt": attempt + 1,
                        },
                    )
                else:
                    # Non-retryable HTTP error - raise immediately
                    logger.error(
                        f"Non-retryable HTTP error {e.response.status_code}",
                        extra={
                            "session_id": session_id,
                            "status_code": e.response.status_code,
                        },
                    )
                    raise

            except ValueError as e:
                # Invalid JSON or missing response field - don't retry
                logger.error(
                    f"Invalid backend response: {e}",
                    extra={"session_id": session_id},
                )
                raise

            # Calculate backoff sleep: 1s, 2s, 4s (2^attempt)
            if attempt < MAX_ATTEMPTS - 1:
                sleep_time = 2**attempt
                # Check if sleeping would exceed time budget
                remaining_time = MAX_TOTAL_TIME - (time.monotonic() - start_time)
                if sleep_time > remaining_time:
                    logger.warning(
                        f"Skipping sleep ({sleep_time}s) - would exceed time budget",
                        extra={"session_id": session_id, "remaining_time": remaining_time},
                    )
                    break

                logger.info(
                    f"Sleeping {sleep_time}s before retry",
                    extra={"session_id": session_id, "sleep_seconds": sleep_time},
                )
                await asyncio.sleep(sleep_time)

        # All retries exhausted
        if last_exception:
            logger.error(
                f"All {MAX_ATTEMPTS} retry attempts failed",
                extra={"session_id": session_id, "last_error": str(last_exception)},
            )
            raise last_exception

        raise RuntimeError("Unexpected state: no exception but all retries failed")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
