"""Tests for Configuration Models.

This module contains tests for verifying the behavior and validation of
configuration models used throughout the MockingJ server.
"""
import pytest
from pydantic import ValidationError

from mockingj.models.config import (
    ServerConfig,
    SSLConfig,
    MockConfig,
    ResponseDelayConfig,
    LoggingConfig,
    LogHandlerConfig
)

class TestServerConfig:
    """Test suite for server configuration models."""

    def test_valid_server_config(self):
        """Test creation of valid server configurations."""
        # Basic configuration
        config = ServerConfig(
            host="localhost",
            port=8000
        )
        assert config.host == "localhost"
        assert config.port == 8000
        assert config.debug is False  # Default value

        # Full configuration
        full_config = ServerConfig(
            host="0.0.0.0",
            port=443,
            debug=True,
            ssl=SSLConfig(
                enabled=True,
                cert_file="/path/to/cert.pem",
                key_file="/path/to/key.pem"
            )
        )
        assert full_config.ssl.enabled is True
        assert full_config.ssl.cert_file == "/path/to/cert.pem"

    @pytest.mark.parametrize("invalid_data,error_message", [
        (
            {"host": "localhost", "port": 0},
            "Port number must be between 1 and 65535"
        ),
        (
            {"host": "localhost", "port": 65536},
            "Port number must be between 1 and 65535"
        ),
        (
            {"host": "", "port": 8000},
            "Host cannot be empty"
        )
    ])
    def test_invalid_server_config(self, invalid_data, error_message):
        """Test validation of invalid server configurations."""
        with pytest.raises(ValidationError, match=error_message):
            ServerConfig(**invalid_data)

    def test_ssl_config_validation(self):
        """Test SSL configuration validation."""
        # SSL enabled requires cert and key files
        with pytest.raises(ValidationError):
            SSLConfig(enabled=True)

        # Valid SSL config
        ssl_config = SSLConfig(
            enabled=True,
            cert_file="/path/to/cert.pem",
            key_file="/path/to/key.pem"
        )
        assert ssl_config.cert_file == "/path/to/cert.pem"

        # Files not required if SSL disabled
        disabled_ssl = SSLConfig(enabled=False)
        assert disabled_ssl.enabled is False


class TestMockConfig:
    """Test suite for mock behavior configuration models."""

    def test_valid_mock_config(self):
        """Test creation of valid mock configurations."""
        # Basic configuration
        config = MockConfig(
            seed=12345
        )
        assert config.seed == 12345
        assert config.consistent_responses is True  # Default value
        assert config.cache_enabled is True  # Default value
        assert config.cache_ttl == 300  # Default value

        # Full configuration with response delay
        full_config = MockConfig(
            seed=12345,
            consistent_responses=True,
            cache_enabled=True,
            cache_ttl=600,
            response_delay=ResponseDelayConfig(
                enabled=True,
                min_ms=100,
                max_ms=500
            )
        )
        assert full_config.response_delay.enabled is True
        assert full_config.response_delay.min_ms == 100
        assert full_config.response_delay.max_ms == 500

    def test_response_delay_validation(self):
        """Test validation of response delay configuration."""
        # Min delay cannot be greater than max delay
        with pytest.raises(ValidationError):
            ResponseDelayConfig(
                enabled=True,
                min_ms=500,
                max_ms=100
            )

        # Negative delays not allowed
        with pytest.raises(ValidationError):
            ResponseDelayConfig(
                enabled=True,
                min_ms=-100,
                max_ms=500
            )

    @pytest.mark.parametrize("cache_ttl,valid", [
        (0, False),      # Too low
        (30, True),      # Minimum valid
        (300, True),     # Default
        (86400, True),   # Maximum valid
        (86401, False)   # Too high
    ])
    def test_cache_ttl_validation(self, cache_ttl, valid):
        """Test validation of cache TTL values."""
        if valid:
            config = MockConfig(seed=12345, cache_ttl=cache_ttl)
            assert config.cache_ttl == cache_ttl
        else:
            with pytest.raises(ValidationError):
                MockConfig(seed=12345, cache_ttl=cache_ttl)


class TestLoggingConfig:
    """Test suite for logging configuration models."""

    def test_valid_logging_config(self):
        """Test creation of valid logging configurations."""
        # Basic configuration
        config = LoggingConfig(
            level="INFO"
        )
        assert config.level == "INFO"
        assert config.format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Full configuration with handlers
        full_config = LoggingConfig(
            level="DEBUG",
            format="%(levelname)s: %(message)s",
            handlers={
                "console": LogHandlerConfig(
                    enabled=True,
                    format="detailed"
                ),
                "file": LogHandlerConfig(
                    enabled=True,
                    path="/var/log/mockingj.log",
                    max_size="10MB"
                )
            }
        )
        assert full_config.handlers["console"].enabled is True
        assert full_config.handlers["file"].path == "/var/log/mockingj.log"

    @pytest.mark.parametrize("invalid_data,error_message", [
        (
            {"level": "INVALID"},
            "Invalid log level"
        ),
        (
            {"level": "INFO", "format": ""},
            "Log format cannot be empty"
        )
    ])
    def test_invalid_logging_config(self, invalid_data, error_message):
        """Test validation of invalid logging configurations."""
        with pytest.raises(ValidationError, match=error_message):
            LoggingConfig(**invalid_data)

    def test_log_handler_validation(self):
        """Test validation of log handler configurations."""
        # File handler requires path when enabled
        with pytest.raises(ValidationError):
            LogHandlerConfig(
                enabled=True,
                handler_type="file"
            )

        # Valid file handler
        file_handler = LogHandlerConfig(
            enabled=True,
            handler_type="file",
            path="/var/log/mockingj.log",
            max_size="10MB"
        )
        assert file_handler.path == "/var/log/mockingj.log"

        # Size format validation
        with pytest.raises(ValidationError):
            LogHandlerConfig(
                enabled=True,
                handler_type="file",
                path="/var/log/mockingj.log",
                max_size="invalid"
            )
            