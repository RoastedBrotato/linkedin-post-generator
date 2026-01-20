"""
Logging configuration using loguru.

Provides structured logging with file rotation, retention, and formatting.
"""

import sys
from pathlib import Path
from loguru import logger
from config.settings import get_settings

settings = get_settings()


def setup_logging():
    """
    Configure loguru logger with file and console output.

    Sets up:
    - Console logging with colored output
    - File logging with rotation and retention
    - Different log levels
    - Structured formatting
    """
    # Remove default handler
    logger.remove()

    # Ensure logs directory exists
    logs_dir = settings.storage.logs_dir
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Console handler (if enabled)
    if settings.logging.log_to_console:
        logger.add(
            sys.stdout,
            format=settings.logging.log_format,
            level=settings.logging.level,
            colorize=True,
        )

    # File handler (if enabled)
    if settings.logging.log_to_file:
        # Main log file
        logger.add(
            logs_dir / "app.log",
            format=settings.logging.log_format,
            level=settings.logging.level,
            rotation=settings.logging.rotation,
            retention=settings.logging.retention,
            compression=settings.logging.compression,
            enqueue=True,  # Thread-safe logging
        )

        # Error log file (only errors and critical)
        logger.add(
            logs_dir / "errors.log",
            format=settings.logging.log_format,
            level="ERROR",
            rotation=settings.logging.rotation,
            retention=settings.logging.retention,
            compression=settings.logging.compression,
            enqueue=True,
        )

    logger.info("Logging initialized")
    logger.debug(f"Log level: {settings.logging.level}")
    logger.debug(f"Logs directory: {logs_dir}")


def get_logger():
    """Get configured logger instance"""
    return logger


# Initialize logging on module import
setup_logging()
