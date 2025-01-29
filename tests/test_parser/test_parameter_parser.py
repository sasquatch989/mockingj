"""Tests for Parameter Parsing functionality.

This module contains tests for verifying the correct parsing and validation
of Swagger/OpenAPI parameter definitions.
"""
import pytest
from typing import Dict, Any

from mockingj.parser.swagger import SwaggerParser
from mockingj.parser.exceptions import (
    ParameterValidationError,
    InvalidParameterTypeError
)

# Error message constants
ERR_INVALID_PARAM_TYPE = "Invalid parameter type"
ERR_INVALID_PARAM_LOC = "Invalid parameter location"
ERR_MISSING_REQUIRED = "Missing required parameter field"


class TestParameterParser:
    """Test suite for parameter parsing functionality."""

    def test_parse_query_parameter(self):
        """Test parsing of query parameters with various types."""
        parameters = [
            {
                "name": "limit",
                "in": "query",
                "type": "integer",
                "required": False,
                "default": 10,
                "minimum": 1,
                "maximum": 100
            },
            {
                "name": "filter",
                "in": "query",
                "type": "string",
                "enum": ["active", "pending", "completed"]
            }
        ]

        parser = SwaggerParser()
        parsed = parser._parse_parameters(parameters)

        # Verify first parameter
        assert parsed[0].name == "limit"
        assert parsed[0].location == "query"
        assert parsed[0].type == "integer"
        assert parsed[0].default == 10
        assert parsed[0].minimum == 1
        assert parsed[0].maximum == 100

        # Verify second parameter
        assert parsed[1].name == "filter"
        assert parsed[1].location == "query"
        assert parsed[1].type == "string"
        assert parsed[1].enum == ["active", "pending", "completed"]

    def test_parse_path_parameter(self):
        """Test parsing of path parameters."""
        parameters = [
            {
                "name": "id",
                "in": "path",
                "type": "string",
                "required": True,
                "pattern": "^[a-zA-Z0-9-]+$"
            }
        ]

        parser = SwaggerParser()
        parsed = parser._parse_parameters(parameters)

        assert parsed[0].name == "id"
        assert parsed[0].location == "path"
        assert parsed[0].required is True
        assert parsed[0].pattern == "^[a-zA-Z0-9-]+$"

    def test_parse_header_parameter(self):
        """Test parsing of header parameters."""
        parameters = [
            {
                "name": "X-API-Version",
                "in": "header",
                "type": "string",
                "required": True
            }
        ]

        parser = SwaggerParser()
        parsed = parser._parse_parameters(parameters)

        assert parsed[0].name == "X-API-Version"
        assert parsed[0].location == "header"
        assert parsed[0].required is True

    def test_parse_body_parameter(self):
        """Test parsing of body parameter with schema."""
        parameters = [
            {
                "name": "user",
                "in": "body",
                "required": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "age": {"type": "integer", "minimum": 0}
                    },
                    "required": ["name", "email"]
                }
            }
        ]

        parser = SwaggerParser()
        parsed = parser._parse_parameters(parameters)

        assert parsed[0].name == "user"
        assert parsed[0].location == "body"
        assert parsed[0].required is True
        assert parsed[0].schema.type == "object"
        assert "name" in parsed[0].schema.required
        assert "email" in parsed[0].schema.required

    def test_array_parameter(self):
        """Test parsing of array parameters."""
        parameters = [
            {
                "name": "tags",
                "in": "query",
                "type": "array",
                "items": {
                    "type": "string"
                },
                "collectionFormat": "multi"
            }
        ]

        parser = SwaggerParser()
        parsed = parser._parse_parameters(parameters)

        assert parsed[0].type == "array"
        assert parsed[0].items.type == "string"
        assert parsed[0].collection_format == "multi"

    @pytest.mark.parametrize("invalid_param,expected_error", [
        (
                {"name": "test", "in": "invalid", "type": "string"},
                ERR_INVALID_PARAM_LOC
        ),
        (
                {"name": "test", "in": "query", "type": "invalid"},
                ERR_INVALID_PARAM_TYPE
        ),
        (
                {"in": "query", "type": "string"},  # Missing name
                ERR_MISSING_REQUIRED
        )
    ])
    def test_invalid_parameters(self, invalid_param: Dict[str, Any],
                                expected_error: str):
        """Test handling of invalid parameter specifications."""
        parser = SwaggerParser()
        with pytest.raises(ParameterValidationError, match=expected_error):
            parser._parse_parameters([invalid_param])

    def test_parameter_with_refs(self):
        """Test parsing parameters with references."""
        spec = {
            "parameters": {
                "LimitParam": {
                    "name": "limit",
                    "in": "query",
                    "type": "integer",
                    "default": 10
                }
            }
        }

        parameters = [
            {"$ref": "#/parameters/LimitParam"}
        ]

        parser = SwaggerParser()
        parser.spec = spec  # Set the spec for reference resolution
        parsed = parser._parse_parameters(parameters)

        assert parsed[0].name == "limit"
        assert parsed[0].type == "integer"
        assert parsed[0].default == 10
