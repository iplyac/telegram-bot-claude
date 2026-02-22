"""FastAPI application with Telegram bot integration."""

import asyncio
import hmac
import logging
import sys
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any, Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pythonjsonlogger import jsonlogger
from telegram import Update

from tgbot import config
from tgbot.dispatcher import setup_handlers
from tgbot.services.backend_client import BackendClient
from tgbot.telegram_bot import create_application, start_polling, stop

# Context variable for Cloud Trace ID
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)

# Global logger
logger = logging.getLogger(__name__)


class CloudTraceJsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter with Cloud Trace integration."""

    def __init__(self, project_id: str, *args: Any, **kwargs: Any):
        self.project_id = project_id
        super().__init__(*args, **kwargs)

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        # Add standard fields
        log_record["timestamp"] = self.formatTime(record)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name

        # Add Cloud Trace field if available
        trace_id = trace_id_var.get()
        if trace_id and self.project_id:
            log_record["logging.googleapis.com/trace"] = (
                f"projects/{self.project_id}/traces/{trace_id}"
            )

        # Move extra fields to 'extra' key
        extra_fields = {}
        standard_keys = {
            "timestamp", "level", "logger", "message",
            "logging.googleapis.com/trace", "taskName",
        }
        for key in list(log_record.keys()):
            if key not in standard_keys:
                extra_fields[key] = log_record.pop(key)
        if extra_fields:
            log_record["extra"] = extra_fields


def setup_logging(log_level: str, project_id: str) -> None:
    """Configure JSON logging with Cloud Trace integration."""
    # Create formatter
    formatter = CloudTraceJsonFormatter(
        project_id,
        fmt="%(timestamp)s %(level)s %(logger)s %(message)s",
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add stdout handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


def log_webhook_url_diagnostics(url: str) -> None:
    """Log diagnostic information about webhook URL."""
    whitespace_count = sum(1 for c in url if c.isspace())
    control_char_count = sum(1 for c in url if ord(c) < 32 or ord(c) == 127)

    logger.info(
        "Webhook URL diagnostics",
        extra={
            "url_length": len(url),
            "whitespace_count": whitespace_count,
            "control_char_count": control_char_count,
            "url_repr": repr(url),
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle including bot startup and shutdown."""
    # === STARTUP ===

    # 1. Configure logging first
    project_id = config.get_project_id()
    log_level = config.get_log_level()
    setup_logging(log_level, project_id)

    logger.info("Starting application", extra={"log_level": log_level})

    # 2. Resolve all configuration values
    region = config.get_region()
    service_name = config.get_service_name()
    agent_api_url = config.get_agent_api_url()
    webhook_url = config.get_webhook_url()
    webhook_path = config.get_webhook_path()
    full_webhook_url = config.get_full_webhook_url()

    logger.info(
        "Configuration loaded",
        extra={
            "region": region,
            "service_name": service_name,
            "agent_api_url_configured": agent_api_url is not None,
            "webhook_mode": webhook_url is not None,
        },
    )

    # 3. Get bot token (fail fast if not available)
    try:
        bot_token = config.get_bot_token()
        logger.info("Bot token resolved successfully")
    except ValueError as e:
        logger.critical("Failed to resolve bot token", extra={"error": str(e)})
        raise

    # 4. Get webhook secret
    webhook_secret = config.get_webhook_secret()
    logger.info("Webhook secret resolved")

    # 5. Create BackendClient
    backend_client = BackendClient(agent_api_url)
    logger.info("BackendClient created", extra={"agent_api_url_configured": agent_api_url is not None})

    # 6. Create Telegram Application
    tg_app = create_application(bot_token, update_queue_maxsize=100)

    # 7. Register handlers
    setup_handlers(tg_app, backend_client, project_id, region, service_name)

    # 8. Store in app state
    app.state.tg_app = tg_app
    app.state.webhook_secret = webhook_secret
    app.state.backend_client = backend_client
    app.state.project_id = project_id

    # 9. Determine mode and start accordingly
    polling_task: Optional[asyncio.Task] = None

    if webhook_url:
        # Webhook mode - initialize app and set webhook before yield
        app.state.webhook_mode = True
        app.state.mode = "webhook"
        app.state.webhook_path = webhook_path

        logger.info("Webhook mode selected, setting up webhook")
        log_webhook_url_diagnostics(full_webhook_url)

        try:
            await tg_app.initialize()
            await tg_app.start()

            await tg_app.bot.set_webhook(
                url=full_webhook_url,
                secret_token=webhook_secret,
            )
            logger.info("Webhook set successfully", extra={"webhook_url": full_webhook_url})

        except Exception as e:
            error_msg = str(e)
            logger.critical(f"Failed to set webhook: {error_msg}")

            # Check for 404 (invalid token)
            if "404" in error_msg:
                logger.critical("Invalid bot token detected (404 response from Telegram API)")

            raise
    else:
        # Polling mode
        app.state.webhook_mode = False
        app.state.mode = "polling"
        app.state.webhook_path = webhook_path

        # Start polling as background task
        polling_task = asyncio.create_task(start_polling(tg_app))
        app.state.polling_task = polling_task
        logger.info("Polling mode started")

    app.state.bot_running = True

    # Yield to let FastAPI start serving
    yield

    # === SHUTDOWN ===
    logger.info("Shutting down application")

    # Stop polling task if running
    polling_task = getattr(app.state, "polling_task", None)
    if polling_task and not polling_task.done():
        try:
            await stop(tg_app)
            # Wait for task with timeout
            await asyncio.wait_for(polling_task, timeout=7.0)
        except asyncio.TimeoutError:
            logger.warning("Polling task did not stop in time, cancelling")
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass

    # Close backend client
    await backend_client.close()
    logger.info("BackendClient closed")

    # Shutdown telegram app
    try:
        await tg_app.shutdown()
        logger.info("Telegram application shutdown complete")
    except Exception as e:
        logger.warning(f"Error during telegram app shutdown: {e}")

    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(title="Telegram Bot", lifespan=lifespan)


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    """Extract Cloud Trace header and set context variable."""
    trace_header = request.headers.get("X-Cloud-Trace-Context")
    if trace_header:
        # Format: TRACE_ID/SPAN_ID;o=...
        trace_id = trace_header.split("/")[0]
        trace_id_var.set(trace_id)
    else:
        trace_id_var.set(None)

    response = await call_next(request)
    return response


@app.get("/healthz")
@app.get("/health")
async def healthz() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/healthz/bot")
async def healthz_bot(request: Request) -> dict[str, Any]:
    """Bot status endpoint."""
    return {
        "bot_running": getattr(request.app.state, "bot_running", False),
        "mode": getattr(request.app.state, "mode", "unknown"),
        "webhook_path": getattr(request.app.state, "webhook_path", "/telegram/webhook"),
    }


@app.post("/api/chat")
async def api_chat(request: Request) -> dict[str, str]:
    """
    Chat API endpoint (stub echo service).

    This endpoint is separate from AGENT_API_URL forwarding.
    Bot forwarding uses AGENT_API_URL, not this local endpoint.
    """
    data = await request.json()
    session_id = data.get("session_id", "")
    message = data.get("message", "")

    logger.info(
        "Chat API request",
        extra={"session_id": session_id, "message_length": len(message)},
    )

    return {"response": f"echo: {message}"}


@app.post("/api/image")
async def api_image() -> dict[str, str]:
    """Image API endpoint (stub)."""
    return {"status": "received", "message": "Image processing not implemented"}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> Response:
    """
    Telegram webhook endpoint.

    Validates the secret header and enqueues updates for processing.
    """
    # Get stored values from app state
    webhook_secret = getattr(request.app.state, "webhook_secret", None)
    tg_app = getattr(request.app.state, "tg_app", None)

    # Validate secret header
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")

    if not header_secret or not hmac.compare_digest(header_secret, webhook_secret):
        remote_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")

        logger.warning(
            "Webhook request with invalid or missing secret",
            extra={
                "remote_ip": remote_ip,
                "user_agent": user_agent,
                "header_present": header_secret is not None,
            },
        )
        return Response(status_code=403)

    # Parse webhook payload
    try:
        payload = await request.json()
        update_id = payload.get("update_id")

        logger.info(
            "Webhook received",
            extra={"update_id": update_id},
        )

        # Validate basic structure
        if not isinstance(update_id, int):
            logger.warning("Invalid webhook payload: missing or invalid update_id")
            return Response(status_code=200)

        # Parse into Telegram Update object
        update = Update.de_json(payload, tg_app.bot)

        logger.info(
            "Webhook update parsed",
            extra={"update_id": update_id},
        )

        # Enqueue for processing
        try:
            tg_app.update_queue.put_nowait(update)
            logger.info(
                "Webhook update queued",
                extra={"update_id": update_id},
            )
        except asyncio.QueueFull:
            logger.error(
                "Update queue full, dropping update",
                extra={"update_id": update_id},
            )
            # Still return 200 to not expose issues to Telegram
            return Response(status_code=200)

    except Exception as e:
        logger.warning(
            f"Webhook processing error: {type(e).__name__}: {e}",
        )
        # Return 200 to not expose errors to Telegram
        return Response(status_code=200)

    return Response(status_code=200)


if __name__ == "__main__":
    import uvicorn

    port = config.get_port()
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        timeout_graceful_shutdown=9,
    )
