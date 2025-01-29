"""Tests for Configuration Management System.

This module contains tests for verifying the correct loading, validation,
and access of configuration settings for the MockingJ server.
"""
import os
from pathlib import Path
from typing import Dict, Any

import pytest
import yaml
from pydantic import ValidationError as PydanticValidationError

from mockingj.core.config import Config
from mockingj.core.exceptions import ValidationError
from mockingj.models.config import ServerConfig, MockConfig, LoggingConfig


class TestConfig:
    """Test suite for configuration management functionality."""

    def test_config_initialization(self):
        """Test basic configuration initialization."""
        config = Config()
        assert config is not None
        assert isinstance(config.server, ServerConfig)
        assert isinstance(config.mock, MockConfig)
        assert isinstance(config.logging, LoggingConfig)

    def test_load_valid_yaml_config(self, temp_dir):
        """Test loading a valid YAML configuration file."""
        # Create test config file
        config_content = """
        server:
          host: localhost
          port: 8000
          debug: true
        mock:
          seed: 12345
          consistent_responses: true
          cache_enabled: true
          cache_ttl: 300
        logging:
          level: DEBUG
          format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        """
        config_file = temp_dir / "config.yaml"
        config_file.write_text(config_content)

        # Load and verify config
        config = Config.load_from_file(config_file)
        assert config.server.host == "localhost"
        assert config.server.port == 8000
        assert config.server.debug is True
        assert config.mock.seed == 12345
        assert config.mock.cache_ttl == 300
        assert config.logging.level == "DEBUG"

    def test_missing_required_sections(self, temp_dir):
        """Test handling of missing required configuration sections."""
        config_content = """
        server:
          host: localhost
          port: 8000
        """
        config_file = temp_dir / "config.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ValidationError) as exc_info:
            Config.load_from_file(config_file)
        
        error_msg = str(exc_info.value)
        assert "Missing required sections:" in error_msg
        assert "mock" in error_msg
        assert "logging" in error_msg

    @pytest.mark.parametrize("invalid_config,expected_error", [
        (
            {
                "server": {"port": -1},
                "mock": {"seed": 12345},
                "logging": {"level": "INFO"}
            },
            "host: Field required; port: Input should be greater than 0"
        ),
        (
            {
                "server": {"host": "localhost"},
                "mock": {"seed": 12345},
                "logging": {"level": "INFO"}
            },
            "port: Field required"
        ),
        (
            "invalid_yaml",
            "Invalid configuration format"
        )
    ])
    def test_invalid_configurations(self, invalid_config, expected_error, temp_dir):
        """Test handling of invalid configuration specifications."""
        config_file = temp_dir / "invalid_config.yaml"

        # Handle the case where invalid_config is a string (invalid YAML)
        if isinstance(invalid_config, str):
            config_file.write_text(invalid_config)
        else:
            config_file.write_text(yaml.dump(invalid_config))

        with pytest.raises(ValidationError) as exc_info:
            Config.load_from_file(config_file)

        assert expected_error in str(exc_info.value)

    def test_environment_variable_override(self, temp_dir):
        """Test that environment variables override file configuration."""
        # Create base config file
        config_content = """
        server:
          host: localhost
          port: 8000
        mock:
          seed: 12345
        logging:
          level: INFO
        """
        config_file = temp_dir / "config.yaml"
        config_file.write_text(config_content)

        # Set environment variables
        os.environ["MOCKINGJ_SERVER_PORT"] = "9000"
        os.environ["MOCKINGJ_MOCK_SEED"] = "54321"

        try:
            # Load config and verify overrides
            config = Config.load_from_file(config_file)
            assert config.server.port == 9000
            assert config.mock.seed == 54321
            # Original values should remain unchanged
            assert config.server.host == "localhost"
            assert config.logging.level == "INFO"
        finally:
            # Clean up environment
            del os.environ["MOCKINGJ_SERVER_PORT"]
            del os.environ["MOCKINGJ_MOCK_SEED"]
            