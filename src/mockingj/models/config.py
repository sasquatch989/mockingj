"""Configuration Model Definitions.

This module contains Pydantic models for configuration validation and type safety.

File path: src/mockingj/models/config.py
"""
from typing import Dict, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


class SSLConfig(BaseModel):
    """SSL/TLS configuration settings."""
    enabled: bool = False
    cert_file: Optional[str] = None
    key_file: Optional[str] = None

    @field_validator("cert_file", "key_file")
    @classmethod
    def validate_ssl_files(cls, v: Optional[str], info: Dict) -> Optional[str]:
        """Validate SSL certificate and key files."""
        if info.data.get("enabled", False) and not v:
            raise ValueError("SSL files required when SSL is enabled")
        return v


class ServerConfig(BaseModel):
    """Server-specific configuration settings."""
    host: str = Field(..., min_length=1)
    port: int = Field(..., gt=0, le=65535)
    debug: bool = False
    ssl: SSLConfig = SSLConfig()

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate host string."""
        if not v:
            raise ValueError("Host cannot be empty")
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number."""
        if v < 1 or v > 65535:
            raise ValueError("Port number must be between 1 and 65535")
        return v


class ResponseDelayConfig(BaseModel):
    """Configuration for simulated response delays."""
    enabled: bool = False
    min_ms: int = Field(0, ge=0)
    max_ms: int = Field(100, gt=0)

    @field_validator("max_ms")
    @classmethod
    def validate_delays(cls, v: int, info: Dict) -> int:
        """Validate delay range."""
        min_ms = info.data.get("min_ms", 0)
        if v < min_ms:
            raise ValueError("Maximum delay must be greater than minimum delay")
        return v


class MockConfig(BaseModel):
    """Configuration for mock behavior."""
    seed: int = Field(..., description="Random seed for consistent generation")
    consistent_responses: bool = True
    cache_enabled: bool = True
    cache_ttl: int = Field(
        300,
        ge=30,
        le=86400,
        description="Cache TTL in seconds"
    )
    response_delay: ResponseDelayConfig = ResponseDelayConfig()


class LogHandlerConfig(BaseModel):
    """Configuration for individual log handlers."""
    enabled: bool = False
    handler_type: str = "console"
    path: Optional[str] = None
    format: str = "default"
    max_size: str = "10MB"

    @field_validator("max_size")
    @classmethod
    def validate_size_format(cls, v: str) -> str:
        """Validate size string format."""
        pattern = r"^\d+(\.\d+)?(B|KB|MB|GB)$"
        if not re.match(pattern, v, re.I):
            raise ValueError("Invalid size format. Use B, KB, MB, or GB suffix")
        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Optional[str], info: Dict) -> Optional[str]:
        """Validate log file path."""
        if info.data.get("handler_type") == "file" and info.data.get("enabled"):
            if not v:
                raise ValueError("Path required for file handler")
        return v


class LoggingConfig(BaseModel):
    """Configuration for logging system."""
    level: str = Field(
        "INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"
    )
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers: Dict[str, LogHandlerConfig] = {}

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate log format string."""
        if not v:
            raise ValueError("Log format cannot be empty")
        return v

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError("Invalid log level")
        return v.upper()

    @field_validator("handlers")
    @classmethod
    def validate_handlers(cls, v: Dict[str, LogHandlerConfig]) -> Dict[str, LogHandlerConfig]:
        """Validate log handlers configuration."""
        if not isinstance(v, dict):
            raise ValueError("Handlers must be a dictionary")

        validated_handlers = {}
        for name, handler in v.items():
            if isinstance(handler, dict):
                validated_handlers[name] = LogHandlerConfig(**handler)
            else:
                validated_handlers[name] = handler
        return validated_handlers


# Configure all models to use Pydantic v2 behavior
model_config = ConfigDict(
    validate_assignment=True,
    arbitrary_types_allowed=True,
    extra='forbid'
)

# Apply the configuration to all models
SSLConfig.model_config = model_config
ServerConfig.model_config = model_config
ResponseDelayConfig.model_config = model_config
MockConfig.model_config = model_config
LogHandlerConfig.model_config = model_config
LoggingConfig.model_config = model_config