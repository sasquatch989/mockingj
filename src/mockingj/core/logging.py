"""Logging Configuration Module.

This module provides centralized logging configuration for the MockingJ server.
It supports multiple handlers, custom formatters, and different logging levels
based on configuration settings.

File path: src/mockingj/core/logging.py
"""
import logging
import logging.config
import logging.handlers
import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import ValidationError

from mockingj.models.config import LoggingConfig, LogHandlerConfig


class LoggingManager:
    """Manages logging configuration and setup for MockingJ.

    This class handles the initialization and management of logging across
    the application, supporting multiple handlers and formats.

    Attributes:
        config: The logging configuration settings
        log_dir: Directory for log files
        initialized: Flag indicating if logging has been initialized
    """

    def __init__(self, config: LoggingConfig, log_dir: Optional[Path] = None) -> None:
        """Initialize the logging manager.

        Args:
            config: Logging configuration settings
            log_dir: Optional directory for log files. Defaults to ./logs
        """
        self.config = config
        self.log_dir = log_dir or Path("./logs")
        self.initialized = False
        self._loggers: Dict[str, logging.Logger] = {}

    def setup(self) -> None:
        """Set up logging configuration based on settings.

        This method initializes all configured logging handlers and formats.
        It should be called once at application startup.

        Raises:
            OSError: If log directory creation fails
            ValidationError: If logging configuration is invalid
        """
        if self.initialized:
            return

        # Ensure log directory exists
        if not self.log_dir.exists():
            self.log_dir.mkdir(parents=True, exist_ok=True)

        # Basic logging configuration
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": self._setup_formatters(),
            "handlers": self._setup_handlers(),
            "loggers": self._setup_loggers(),
            "root": {
                "level": self.config.level,
                "handlers": self._get_enabled_handlers()
            }
        }

        try:
            logging.config.dictConfig(logging_config)
            self.initialized = True
        except Exception as e:
            raise ValidationError(
                "Failed to initialize logging configuration"
            ) from e

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance by name.

        Args:
            name: Name of the logger to retrieve

        Returns:
            Logger instance configured according to settings
        """
        if not self.initialized:
            self.setup()

        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)

        return self._loggers[name]

    def _setup_formatters(self) -> Dict[str, Dict[str, str]]:
        """Configure log formatters based on settings.

        Returns:
            Dictionary of formatter configurations
        """
        formatters = {
            "default": {
                "format": self.config.format
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - "
                          "%(pathname)s:%(lineno)d - %(message)s"
            },
            "simple": {
                "format": "%(levelname)s: %(message)s"
            }
        }

        # Add custom formatters from config if defined
        if hasattr(self.config, "formatters"):
            formatters.update(self.config.formatters)

        return formatters

    def _setup_handlers(self) -> Dict[str, Dict[str, Any]]:
        """Configure log handlers based on settings.

        Returns:
            Dictionary of handler configurations
        """
        handlers: Dict[str, Dict[str, Any]] = {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": self.config.level
            }
        }

        # Configure file handler if enabled
        if self.config.handlers.get("file", LogHandlerConfig()).enabled:
            file_config = self.config.handlers["file"]
            log_file = self.log_dir / "mockingj.log"

            handlers["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(log_file),
                "formatter": "detailed",
                "maxBytes": self._parse_size(file_config.max_size),
                "backupCount": 5,
                "encoding": "utf8"
            }

        # Configure error log if enabled
        if self.config.handlers.get("error", LogHandlerConfig()).enabled:
            error_file = self.log_dir / "error.log"

            handlers["error"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(error_file),
                "formatter": "detailed",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8",
                "level": "ERROR"
            }

        return handlers

    def _setup_loggers(self) -> Dict[str, Dict[str, Any]]:
        """Configure individual loggers based on settings.

        Returns:
            Dictionary of logger configurations
        """
        loggers = {
            "mockingj": {
                "level": self.config.level,
                "handlers": self._get_enabled_handlers(),
                "propagate": False
            },
            "mockingj.api": {
                "level": self.config.level,
                "handlers": self._get_enabled_handlers(),
                "propagate": False
            },
            "mockingj.parser": {
                "level": self.config.level,
                "handlers": self._get_enabled_handlers(),
                "propagate": False
            }
        }

        # Add custom loggers from config if defined
        if hasattr(self.config, "loggers"):
            loggers.update(self.config.loggers)

        return loggers

    def _get_enabled_handlers(self) -> list[str]:
        """Get list of enabled handler names.

        Returns:
            List of enabled handler names
        """
        handlers = ["console"]

        if self.config.handlers.get("file", LogHandlerConfig()).enabled:
            handlers.append("file")

        if self.config.handlers.get("error", LogHandlerConfig()).enabled:
            handlers.append("error")

        return handlers

    @staticmethod
    def _parse_size(size_str: str) -> int:
        """Parse size string (e.g., '10MB') to bytes.

        Args:
            size_str: Size string with unit suffix

        Returns:
            Size in bytes

        Raises:
            ValueError: If size string format is invalid
        """
        units = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024
        }

        size_str = size_str.strip().upper()
        if not any(size_str.endswith(unit) for unit in units):
            raise ValueError(f"Invalid size format: {size_str}")

        for unit, multiplier in units.items():
            if size_str.endswith(unit):
                try:
                    number = float(size_str[:-len(unit)])
                    return int(number * multiplier)
                except ValueError as e:
                    raise ValueError(f"Invalid size number: {size_str}") from e

        raise ValueError(f"Unhandled size format: {size_str}")


# Global logging manager instance
_logging_manager: Optional[LoggingManager] = None


def setup_logging(config: LoggingConfig, log_dir: Optional[Path] = None) -> None:
    """Initialize global logging configuration.

    Args:
        config: Logging configuration settings
        log_dir: Optional directory for log files

    Raises:
        RuntimeError: If logging is already initialized
    """
    global _logging_manager

    if _logging_manager is not None:
        raise RuntimeError("Logging already initialized")

    _logging_manager = LoggingManager(config, log_dir)
    _logging_manager.setup()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance by name.

    Args:
        name: Name of the logger to retrieve

    Returns:
        Configured logger instance

    Raises:
        RuntimeError: If logging is not initialized
    """
    if _logging_manager is None:
        raise RuntimeError(
            "Logging not initialized. Call setup_logging() first."
        )

    return _logging_manager.get_logger(name)
