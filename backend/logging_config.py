#!/usr/bin/env python3
"""
Centralized Logging Configuration for Piano LED Visualizer
Provides consistent logging setup across all modules
"""

import logging
import sys
from typing import Optional

# Default logging format
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Default logging level
DEFAULT_LEVEL = logging.INFO

def setup_logging(
    level: Optional[int] = None,
    format_string: Optional[str] = None,
    log_to_file: bool = False,
    log_file: Optional[str] = None
) -> None:
    """
    Setup centralized logging configuration.

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
        format_string: Log format string
        log_to_file: Whether to log to file in addition to console
        log_file: Path to log file (if log_to_file is True)
    """
    level = level or DEFAULT_LEVEL
    format_string = format_string or DEFAULT_FORMAT

    # Create formatter
    formatter = logging.Formatter(format_string)

    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    root_logger.addHandler(console_handler)

    # Add file handler if requested
    if log_to_file and log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(level)
            root_logger.addHandler(file_handler)
        except (OSError, IOError) as e:
            # If file logging fails, log to console only
            console_handler.emit(
                logging.LogRecord(
                    name='logging_config',
                    level=logging.WARNING,
                    pathname='',
                    lineno=0,
                    msg=f"Failed to setup file logging to {log_file}: {e}",
                    args=(),
                    exc_info=None
                )
            )

    # Prevent duplicate messages from parent loggers
    root_logger.propagate = False

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

# Convenience functions for common logging levels
def log_debug(logger: logging.Logger, message: str, *args, **kwargs) -> None:
    """Log a debug message."""
    logger.debug(message, *args, **kwargs)

def log_info(logger: logging.Logger, message: str, *args, **kwargs) -> None:
    """Log an info message."""
    logger.info(message, *args, **kwargs)

def log_warning(logger: logging.Logger, message: str, *args, **kwargs) -> None:
    """Log a warning message."""
    logger.warning(message, *args, **kwargs)

def log_error(logger: logging.Logger, message: str, *args, **kwargs) -> None:
    """Log an error message."""
    logger.error(message, *args, **kwargs)

def log_critical(logger: logging.Logger, message: str, *args, **kwargs) -> None:
    """Log a critical message."""
    logger.critical(message, *args, **kwargs)