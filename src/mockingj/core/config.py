"""Configuration Management Module.

This module handles loading and managing configuration settings for the MockingJ server.
It supports both YAML file-based configuration and environment variable overrides.

File path: src/mockingj/core/config.py
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional, TypeVar, List, Union

import yaml
from pydantic import ValidationError as PydanticValidationError

from mockingj.core.exceptions import ValidationError
from mockingj.models.config import (
    ServerConfig,
    MockConfig,
    LoggingConfig,
    SSLConfig,
    ResponseDelayConfig,
    LogHandlerConfig
)

T = TypeVar('T')  # Generic type for config sections


class Config:
    """Configuration manager for MockingJ server."""

    ENV_PREFIX = "MOCKINGJ_"

    def __init__(
        self,
        server: Optional[ServerConfig] = None,
        mock: Optional[MockConfig] = None,
        logging: Optional[LoggingConfig] = None
    ) -> None:
        """Initialize configuration with default or provided values."""
        self.server = server or ServerConfig(
            host="localhost",
            port=8000,
            debug=False,
            ssl=SSLConfig(enabled=False)
        )

        self.mock = mock or MockConfig(
            seed=12345,
            consistent_responses=True,
            cache_enabled=True,
            cache_ttl=300,
            response_delay=ResponseDelayConfig(
                enabled=False,
                min_ms=0,
                max_ms=100
            )
        )

        self.logging = logging or LoggingConfig(
            level="INFO",
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers={}
        )

        self._config_path: Optional[Path] = None

    @classmethod
    def load_from_file(cls, config_path: Path) -> "Config":
        """Load configuration from a YAML file."""
        if not config_path.exists():
            raise ValidationError([{
                "msg": f"Config file not found: {config_path}"
            }])

        try:
            with config_path.open("r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError:
            raise ValidationError([{
                "msg": "Invalid configuration format"
            }])

        if not isinstance(config_data, dict):
            raise ValidationError([{
                "msg": "Invalid configuration format"
            }])

        instance = cls()
        instance._config_path = config_path
        try:
            instance._load_config_data(config_data)
            instance._apply_environment_overrides()
        except PydanticValidationError as e:
            # Convert Pydantic errors to our format
            errors = []
            for err in e.errors():
                field_path = '.'.join(str(loc) for loc in err['loc'])
                errors.append({
                    'loc': err['loc'],
                    'msg': err['msg']
                })
            raise ValidationError(errors)

        return instance

    def _convert_pydantic_errors(
        self,
        e: PydanticValidationError
    ) -> List[Dict[str, Any]]:
        """Convert Pydantic validation errors to our format."""
        errors = []
        for error in e.errors():
            field = error.get("loc", ())[-1] if error.get("loc") else ""
            msg = error.get("msg", "Unknown error")
            errors.append({
                "loc": (field,) if field else (),
                "msg": msg
            })
        return sorted(errors, key=lambda x: x["loc"][0] if x["loc"] else "")

    def _load_config_data(self, config_data: Dict[str, Any]) -> None:
        """Load configuration data into appropriate sections."""
        errors = []
        
        # Check for required sections
        missing = []
        for section in ["server", "mock", "logging"]:
            if section not in config_data:
                missing.append(section)

        if missing:
            errors.append({
                "msg": f"Missing required sections: {', '.join(missing)}"
            })
            raise ValidationError(errors)

        try:
            self.server = ServerConfig(**config_data.get("server", {}))
            self.mock = MockConfig(**config_data.get("mock", {}))
            self.logging = LoggingConfig(**config_data.get("logging", {}))
        except PydanticValidationError as e:
            # Convert validation errors to our format
            raise ValidationError(self._convert_pydantic_errors(e))

    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        env_vars = {
            k[len(self.ENV_PREFIX):]: v
            for k, v in os.environ.items()
            if k.startswith(self.ENV_PREFIX)
        }

        if env_vars:
            self._apply_env_to_section("SERVER", env_vars, self.server)
            self._apply_env_to_section("MOCK", env_vars, self.mock)
            self._apply_env_to_section("LOGGING", env_vars, self.logging)

    def _apply_env_to_section(
        self,
        prefix: str,
        env_vars: Dict[str, str],
        config_section: T
    ) -> None:
        """Apply environment variables to a specific configuration section."""
        section_vars = {
            k.lower(): v
            for k, v in env_vars.items()
            if k.startswith(f"{prefix}_")
        }

        if section_vars:
            model_class = type(config_section)
            update_data = config_section.model_dump()

            for key, value in section_vars.items():
                field_name = key.split("_", 1)[1] if "_" in key else key
                if hasattr(config_section, field_name):
                    try:
                        field_type = type(getattr(config_section, field_name))
                        update_data[field_name] = self._convert_env_value(
                            value,
                            field_type
                        )
                    except (ValueError, TypeError) as e:
                        raise ValidationError([{
                            "loc": (prefix.lower(), field_name),
                            "msg": str(e)
                        }])

            try:
                new_section = model_class(**update_data)
                setattr(self, prefix.lower(), new_section)
            except PydanticValidationError as e:
                raise ValidationError(self._convert_pydantic_errors(e))

    @staticmethod
    def _convert_env_value(value: str, target_type: type) -> Any:
        """Convert environment variable string to appropriate type."""
        if target_type == bool:
            return value.lower() in ("true", "1", "yes", "on")
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == list:
            return [item.strip() for item in value.split(",")]
        else:
            return value
        