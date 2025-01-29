"""PyTest Configuration and Fixtures.

This module contains all the pytest fixtures and configuration needed for testing MockingJ.
Fixtures are organized by their scope and usage area.
"""
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator

import pytest
from fastapi.testclient import TestClient

# Constants for test data
TEST_DATA_DIR = Path(__file__).parent / "test_data"
SAMPLE_SWAGGER_FILE = TEST_DATA_DIR / "sample_swagger.json"

# Configure pytest-asyncio
def pytest_configure(config):
    """PyTest configuration hook."""
    # Create test data directory if it doesn't exist
    TEST_DATA_DIR.mkdir(exist_ok=True)

    # Set default asyncio fixture loop scope to function
    config.option.asyncio_default_fixture_loop_scope = "function"

    # Add test markers
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Fixture providing the test data directory path."""
    return TEST_DATA_DIR


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provides a temporary directory for test file operations."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_swagger_content() -> Dict[str, Any]:
    """Provides a sample swagger specification as a dictionary."""
    return {
        "swagger": "2.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0"
        },
        "paths": {
            "/test": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "message": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_server_config() -> Dict[str, Any]:
    """Provides test configuration for the mock server."""
    return {
        "server": {
            "host": "localhost",
            "port": 8000,
            "debug": True
        },
        "mock": {
            "seed": 12345,
            "consistent_responses": True,
            "cache_enabled": True,
            "cache_ttl": 300
        },
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }


@pytest.fixture
def sample_openapi_types() -> Dict[str, Dict[str, Any]]:
    """Provides sample OpenAPI type definitions for testing generators."""
    return {
        "string": {
            "type": "string",
            "maxLength": 100,
            "minLength": 1,
            "format": "email"
        },
        "integer": {
            "type": "integer",
            "maximum": 100,
            "minimum": 1,
            "format": "int64"
        },
        "array": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 5,
            "minItems": 1
        },
        "object": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"}
            },
            "required": ["id"]
        }
    }


@pytest.fixture
def mock_health_data() -> Dict[str, Any]:
    """Provides mock health check data."""
    return {
        "status": "healthy",
        "uptime": 3600,
        "version": "1.0.0",
        "components": {
            "cache": {"status": "ok"},
            "mock_generator": {"status": "ok"}
        }
    }


@pytest.fixture
def mock_metrics_data() -> Dict[str, Any]:
    """Provides mock metrics data."""
    return {
        "requests": {
            "total": 100,
            "success": 95,
            "failed": 5
        },
        "response_time": {
            "avg": 0.15,
            "p95": 0.45,
            "p99": 0.75
        },
        "cache": {
            "hits": 75,
            "misses": 25
        }
    }


def pytest_collection_modifyitems(items):
    """PyTest hook to modify test items."""
    for item in items:
        # Mark all tests in the integration directory as integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        # Mark all tests in the unit directory as unit tests
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
            