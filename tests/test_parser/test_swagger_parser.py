"""Tests for the Swagger Parser component.

This module contains tests for verifying the correct parsing and validation
of Swagger/OpenAPI specifications.
"""
import json
from pathlib import Path
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from mockingj.parser.swagger import SwaggerParser
from mockingj.parser.exceptions import SwaggerParserError, InvalidSpecificationError

# Constants for error messages
ERR_INVALID_FILE = "Invalid Swagger file format"
ERR_MISSING_REQUIRED = "Missing required field"
ERR_INVALID_VERSION = "Unsupported Swagger version"


class TestSwaggerParser:
    """Test suite for SwaggerParser functionality."""

    def test_parser_initialization(self):
        """Test basic parser initialization."""
        parser = SwaggerParser()
        assert parser is not None
        assert parser.spec is None

    def test_parser_loads_valid_file(self, sample_swagger_content, temp_dir):
        """Test loading a valid Swagger file."""
        # Create temporary swagger file
        swagger_file = temp_dir / "valid_swagger.json"
        swagger_file.write_text(json.dumps(sample_swagger_content))

        parser = SwaggerParser()
        spec = parser.parse(swagger_file)

        assert spec is not None
        assert spec.info.title == "Test API"
        assert spec.info.version == "1.0.0"
        assert "/test" in spec.paths

    def test_parser_invalid_file_raises_error(self, temp_dir):
        """Test that invalid JSON raises appropriate error."""
        invalid_file = temp_dir / "invalid.json"
        invalid_file.write_text("{invalid json")

        parser = SwaggerParser()
        with pytest.raises(SwaggerParserError, match=ERR_INVALID_FILE):
            parser.parse(invalid_file)

    def test_parser_missing_required_fields(self, temp_dir):
        """Test handling of missing required fields."""
        invalid_spec = {
            "swagger": "2.0",
            # Missing 'info' and other required fields
        }

        spec_file = temp_dir / "missing_fields.json"
        spec_file.write_text(json.dumps(invalid_spec))

        parser = SwaggerParser()
        with pytest.raises(InvalidSpecificationError, match=ERR_MISSING_REQUIRED):
            parser.parse(spec_file)

    def test_parser_unsupported_version(self, temp_dir):
        """Test handling of unsupported Swagger versions."""
        invalid_spec = {
            "swagger": "1.0",  # Unsupported version
            "info": {
                "title": "Test API",
                "version": "1.0.0"
            }
        }

        spec_file = temp_dir / "wrong_version.json"
        spec_file.write_text(json.dumps(invalid_spec))

        parser = SwaggerParser()
        with pytest.raises(InvalidSpecificationError, match=ERR_INVALID_VERSION):
            parser.parse(spec_file)
