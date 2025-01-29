"""Core Exception Definitions.

This module contains custom exceptions for the MockingJ core functionality.

File path: src/mockingj/core/exceptions.py
"""
from typing import Any, List, Optional, Tuple, Union


class ConfigurationError(Exception):
    """Base class for configuration-related errors."""

    def __init__(
            self,
            message: str,
            loc: Optional[Tuple[Union[str, int], ...]] = None
    ) -> None:
        """Initialize configuration error.

        Args:
            message: Error message
            loc: Optional location of the error in the configuration
        """
        super().__init__(message)
        self.message = message
        self.loc = loc or tuple()


class ValidationError(ConfigurationError):
    """Raised when configuration validation fails."""

    def __init__(
            self,
            errors: List[dict[str, Any]]
    ) -> None:
        """Initialize validation error.

        Args:
            errors: List of validation errors with locations and messages
        """
        # Format a clear error message from all errors
        message = "; ".join(
            f"{'.'.join(str(l) for l in error.get('loc', ()))}:"
            f" {error.get('msg', 'Unknown error')}"
            for error in errors
        )
        super().__init__(message)
        self.errors = errors
        