"""Backend client service for forwarding messages to the agent API."""

import asyncio
import logging
import time
from dataclasses import dataclass, asdict
from typing import Optional, Any

import httpx

logger = logging.getLogger(__name__)

# Retry configuration
MAX_ATTEMPTS = 3
MAX_TOTAL_TIME = 30.0  # seconds
RETRYABLE_STATUS_CODES = {502, 503, 504}


@dataclass
class TelegramMetadata:
    """Metadata about the Telegram message context."""

    chat_id: int
    user_id: int
    chat_type: str  # "private", "group", "supergroup", or "unknown"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


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

    async def _post_with_retry(
        self, url: str, payload: dict, session_id: str, log_label: str, request_id: str = "",
        timeout: Optional[float] = None, max_total_time: Optional[float] = None,
        response_field: str = "response",
    ) -> dict:
        """
        POST JSON to a URL with retry logic.

        Args:
            url: Target URL
            payload: JSON payload
            session_id: Session ID for logging
            log_label: Label for log messages (e.g. "message", "voice")
            timeout: Per-request timeout override (default: client timeout)
            max_total_time: Total retry budget override (default: MAX_TOTAL_TIME)

        Returns:
            Parsed JSON response as dict

        Raises:
            ValueError: If response is invalid
            httpx.HTTPError: If all retry attempts fail
        """
        effective_max_total_time = max_total_time if max_total_time is not None else MAX_TOTAL_TIME
        start_time = time.monotonic()
        last_exception: Optional[Exception] = None

        for attempt in range(MAX_ATTEMPTS):
            elapsed = time.monotonic() - start_time
            if elapsed >= effective_max_total_time:
                logger.warning(
                    f"Retry budget exhausted after {elapsed:.1f}s",
                    extra={"session_id": session_id, "attempts": attempt},
                )
                break

            try:
                request_start = time.monotonic()
                endpoint = url.split("/")[-1] if "/" in url else url

                logger.info(
                    f"Agent request start",
                    extra={
                        "request_id": request_id,
                        "session_id": session_id,
                        "endpoint": f"/api/{endpoint}",
                        "attempt": attempt + 1,
                    },
                )

                response = await self._client.post(url, json=payload, timeout=timeout)
                response.raise_for_status()

                data = response.json()
                if response_field not in data:
                    raise ValueError(f"Missing '{response_field}' field in backend response")

                latency_ms = int((time.monotonic() - request_start) * 1000)
                logger.info(
                    f"Agent response received",
                    extra={
                        "request_id": request_id,
                        "session_id": session_id,
                        "status_code": response.status_code,
                        "latency_ms": latency_ms,
                    },
                )
                return data

            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                last_exception = e
                logger.warning(
                    f"Connection error on attempt {attempt + 1}: {type(e).__name__}",
                    extra={
                        "request_id": request_id,
                        "session_id": session_id,
                        "error_type": type(e).__name__,
                        "attempt": attempt + 1,
                    },
                )

            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code in RETRYABLE_STATUS_CODES:
                    logger.warning(
                        f"Retryable HTTP error {e.response.status_code} on attempt {attempt + 1}",
                        extra={
                            "request_id": request_id,
                            "session_id": session_id,
                            "status_code": e.response.status_code,
                            "attempt": attempt + 1,
                        },
                    )
                else:
                    logger.error(
                        f"Non-retryable HTTP error {e.response.status_code}",
                        extra={
                            "request_id": request_id,
                            "session_id": session_id,
                            "status_code": e.response.status_code,
                            "error_type": "HTTPStatusError",
                        },
                    )
                    raise

            except ValueError as e:
                logger.error(
                    f"Invalid backend response: {e}",
                    extra={
                        "request_id": request_id,
                        "session_id": session_id,
                        "error_type": "ValueError",
                        "error_message": str(e),
                    },
                )
                raise

            if attempt < MAX_ATTEMPTS - 1:
                sleep_time = 2**attempt
                remaining_time = effective_max_total_time - (time.monotonic() - start_time)
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

        if last_exception:
            logger.error(
                f"All {MAX_ATTEMPTS} retry attempts failed",
                extra={
                    "request_id": request_id,
                    "session_id": session_id,
                    "error_type": type(last_exception).__name__,
                    "error_message": str(last_exception),
                },
            )
            raise last_exception

        raise RuntimeError("Unexpected state: no exception but all retries failed")

    async def forward_message(
        self,
        conversation_id: str,
        message: str,
        metadata: Optional[TelegramMetadata] = None,
        request_id: str = "",
    ) -> str:
        """
        Forward a text message to the backend agent API.

        Args:
            conversation_id: Conversation identifier (format: "tg_dm_{user_id}" or "tg_group_{chat_id}")
            message: User message text
            metadata: Telegram metadata (chat_id, user_id, chat_type)
            request_id: Correlation ID for logging

        Returns:
            Response text from the backend

        Raises:
            ValueError: If AGENT_API_URL is not configured or response is invalid
            httpx.HTTPError: If all retry attempts fail
        """
        if self.agent_api_url is None:
            raise ValueError("AGENT_API_URL is not configured")

        url = f"{self.agent_api_url.rstrip('/')}/api/chat"
        payload: dict[str, Any] = {
            "conversation_id": conversation_id,
            "message": message,
        }

        if metadata:
            payload["metadata"] = {"telegram": metadata.to_dict()}

        data = await self._post_with_retry(url, payload, conversation_id, "message", request_id)
        return data["response"]

    async def forward_voice(
        self,
        conversation_id: str,
        audio_base64: str,
        mime_type: str = "audio/ogg",
        metadata: Optional[TelegramMetadata] = None,
        request_id: str = "",
    ) -> dict:
        """
        Forward a voice message to the backend agent API.

        Args:
            conversation_id: Conversation identifier (format: "tg_dm_{user_id}" or "tg_group_{chat_id}")
            audio_base64: Base64-encoded audio bytes
            mime_type: Audio MIME type (default: "audio/ogg")
            metadata: Telegram metadata (chat_id, user_id, chat_type)
            request_id: Correlation ID for logging

        Returns:
            Dict with "response" and "transcription" keys

        Raises:
            ValueError: If AGENT_API_URL is not configured or response is invalid
            httpx.HTTPError: If all retry attempts fail
        """
        if self.agent_api_url is None:
            raise ValueError("AGENT_API_URL is not configured")

        url = f"{self.agent_api_url.rstrip('/')}/api/voice"
        payload: dict[str, Any] = {
            "conversation_id": conversation_id,
            "audio_base64": audio_base64,
            "mime_type": mime_type,
        }

        if metadata:
            payload["metadata"] = {"telegram": metadata.to_dict()}

        audio_size = len(audio_base64) * 3 // 4  # approximate decoded size
        logger.info(
            "Forwarding voice to backend",
            extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "audio_size_bytes": audio_size,
                "mime_type": mime_type,
            },
        )

        return await self._post_with_retry(url, payload, conversation_id, "voice", request_id)

    async def forward_image(
        self,
        conversation_id: str,
        image_base64: str,
        mime_type: str = "image/jpeg",
        prompt: str = "What is in this image?",
        metadata: Optional[TelegramMetadata] = None,
        request_id: str = "",
    ) -> dict:
        """
        Forward an image to the backend agent API.

        Args:
            conversation_id: Conversation identifier (format: "tg_dm_{user_id}" or "tg_group_{chat_id}")
            image_base64: Base64-encoded image bytes
            mime_type: Image MIME type (default: "image/jpeg")
            prompt: Question or instruction for image analysis
            metadata: Telegram metadata (chat_id, user_id, chat_type)
            request_id: Correlation ID for logging

        Returns:
            Dict with "response" and optionally "description" keys

        Raises:
            ValueError: If AGENT_API_URL is not configured or response is invalid
            httpx.HTTPError: If all retry attempts fail
        """
        if self.agent_api_url is None:
            raise ValueError("AGENT_API_URL is not configured")

        url = f"{self.agent_api_url.rstrip('/')}/api/image"
        payload: dict[str, Any] = {
            "conversation_id": conversation_id,
            "image_base64": image_base64,
            "mime_type": mime_type,
            "prompt": prompt,
        }

        if metadata:
            payload["metadata"] = {"telegram": metadata.to_dict()}

        image_size = len(image_base64) * 3 // 4  # approximate decoded size
        logger.info(
            "Forwarding image to backend",
            extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "image_size_bytes": image_size,
                "mime_type": mime_type,
                "prompt_length": len(prompt),
            },
        )

        return await self._post_with_retry(
            url, payload, conversation_id, "image", request_id,
            timeout=120.0, max_total_time=180.0,
        )

    async def forward_document(
        self,
        conversation_id: str,
        document_base64: str,
        mime_type: str = "application/octet-stream",
        filename: str = "document",
        prompt: Optional[str] = None,
        metadata: Optional[TelegramMetadata] = None,
        request_id: str = "",
    ) -> dict:
        """
        Forward a document to the backend agent API.

        Args:
            conversation_id: Conversation identifier (format: "tg_dm_{user_id}" or "tg_group_{chat_id}")
            document_base64: Base64-encoded document bytes
            mime_type: Document MIME type (default: "application/octet-stream")
            filename: Original filename (default: "document")
            prompt: Optional user caption / instruction for the document
            metadata: Telegram metadata (chat_id, user_id, chat_type)
            request_id: Correlation ID for logging

        Returns:
            Dict with "response" key

        Raises:
            ValueError: If AGENT_API_URL is not configured or response is invalid
            httpx.HTTPError: If all retry attempts fail
        """
        if self.agent_api_url is None:
            raise ValueError("AGENT_API_URL is not configured")

        url = f"{self.agent_api_url.rstrip('/')}/api/document"
        payload: dict[str, Any] = {
            "conversation_id": conversation_id,
            "document_base64": document_base64,
            "mime_type": mime_type,
            "filename": filename,
        }

        if prompt:
            payload["prompt"] = prompt

        if metadata:
            payload["metadata"] = {"telegram": metadata.to_dict()}

        doc_size = len(document_base64) * 3 // 4  # approximate decoded size
        logger.info(
            "Forwarding document to backend",
            extra={
                "request_id": request_id,
                "conversation_id": conversation_id,
                "doc_size_bytes": doc_size,
                "mime_type": mime_type,
                "doc_filename": filename,
            },
        )

        data = await self._post_with_retry(
            url, payload, conversation_id, "document", request_id,
            timeout=120.0, max_total_time=180.0,
            response_field="content",
        )
        # Normalize: master-agent document endpoint returns "content", handlers expect "response"
        data["response"] = data.pop("content")
        return data

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
