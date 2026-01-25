"""Telegram bot module for creating and managing the bot application."""

import asyncio
import logging

from telegram.ext import Application

logger = logging.getLogger(__name__)


def create_application(bot_token: str, update_queue_maxsize: int = 100) -> Application:
    """
    Create and configure a Telegram Application.

    Args:
        bot_token: Telegram bot token
        update_queue_maxsize: Maximum size of the update queue (default: 100)

    Returns:
        Configured Application instance (not started)
    """
    # Create bounded queue for update processing
    update_queue: asyncio.Queue = asyncio.Queue(maxsize=update_queue_maxsize)

    # Build application with concurrent updates limit
    application = (
        Application.builder()
        .token(bot_token)
        .concurrent_updates(100)
        .update_queue(update_queue)
        .build()
    )

    logger.info(
        "Telegram application created",
        extra={"update_queue_maxsize": update_queue_maxsize, "concurrent_updates": 100},
    )

    return application


async def start_polling(application: Application) -> None:
    """
    Start the bot in polling mode.

    This function initializes the application and starts polling for updates.
    It runs until the application is stopped.

    Args:
        application: Configured Application instance
    """
    logger.info("Starting bot in polling mode")

    await application.initialize()
    await application.start()

    if application.updater:
        await application.updater.start_polling(drop_pending_updates=True)
        logger.info("Polling started successfully")
    else:
        logger.error("Updater not available, cannot start polling")


async def stop(application: Application) -> None:
    """
    Stop the bot application gracefully.

    Args:
        application: Running Application instance
    """
    logger.info("Stopping bot application")

    try:
        if application.updater and application.updater.running:
            await application.updater.stop()
            logger.info("Updater stopped")
    except Exception as e:
        logger.warning(f"Error stopping updater: {e}")

    try:
        await application.stop()
        logger.info("Application stopped")
    except Exception as e:
        logger.warning(f"Error stopping application: {e}")

    try:
        await application.shutdown()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.warning(f"Error during shutdown: {e}")
