"""Tests for Response Parsing functionality.

This module contains tests for verifying the correct parsing and validation
of Swagger/OpenAPI response definitions.
"""
import pytest
from typing import Dict, Any

from mockingj.parser.swagger import SwaggerParser
from mockingj.parser.exceptions import (
    ResponseValidationError,
    InvalidStatusCodeError
)

# Error message constants
ERR_INVALID_STATUS = "Invalid status code"
ERR_MISSING_SCHEMA = "Missing response schema"
ERR_INVALID_HEADER = "Invalid header specification"


class TestResponseParser:
    """Test suite for response parsing functionality."""

    def test_parse_basic_response(self):
        """Test parsing of basic response definition."""
        responses = {
            "200": {
                "description": "Successful response",
                "schema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"}
                    }
                }
            }
        }

        parser = SwaggerParser()
        parsed = parser._parse_responses(responses)

        assert "200" in parsed
        assert parsed["200"].description == "Successful response"
        assert parsed["200"].schema.type == "object"
        assert "id" in parsed["200"].schema.properties
        assert "name" in parsed["200"].schema.properties

    def test_parse_response_headers(self):
        """Test parsing of response headers."""
        responses = {
            "200": {
                "description": "Success",
                "headers": {
                    "X-Rate-Limit": {
                        "type": "integer",
                        "format": "int32",
                        "description": "Calls per hour allowed"
                    },
                    "X-Expires-After": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Date in UTC when token expires"
                    }
                }
            }
        }

        parser = SwaggerParser()
        parsed = parser._parse_responses(responses)

        headers = parsed["200"].headers
        assert "X-Rate-Limit" in headers
        assert headers["X-Rate-Limit"].type == "integer"
        assert headers["X-Rate-Limit"].format == "int32"

        assert "X-Expires-After" in headers
        assert headers["X-Expires-After"].type == "string"
        assert headers["X-Expires-After"].format == "date-time"

    def test_parse_array_response(self):
        """Test parsing of array response schema."""
        responses = {
            "200": {
                "description": "A list of items",
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"}
                        }
                    }
                }
            }
        }

        parser = SwaggerParser()
        parsed = parser._parse_responses(responses)

        assert parsed["200"].schema.type == "array"
        assert parsed["200"].schema.items.type == "object"
        assert "id" in parsed["200"].schema.items.properties

    def test_error_responses(self):
        """Test parsing of error response definitions."""
        responses = {
            "400": {
                "description": "Bad request",
                "schema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "integer"},
                        "message": {"type": "string"}
                    }
                }
            },
            "404": {
                "description": "Not found",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"}
                    }
                }
            }
        }

        parser = SwaggerParser()
        parsed = parser._parse_responses(responses)

        assert "400" in parsed
        assert "404" in parsed
        assert parsed["400"].schema.properties["code"].type == "integer"
        assert parsed["404"].schema.properties["message"].type == "string"

    @pytest.mark.parametrize("invalid_responses,expected_error", [
        (
                {"600": {"description": "Invalid"}},
                ERR_INVALID_STATUS
        ),
        (
                {"200": {}},  # Missing description
                "Missing response description"
        ),
        (
                {"200": {"description": "Success", "headers": {"Invalid": {}}}},
                ERR_INVALID_HEADER
        )
    ])
    def test_invalid_responses(self, invalid_responses: Dict[str, Any],
                               expected_error: str):
        """Test handling of invalid response specifications."""
        parser = SwaggerParser()
        with pytest.raises(ResponseValidationError, match=expected_error):
            parser._parse_responses(invalid_responses)

    def test_response_reference(self):
        """Test parsing responses with references."""
        spec = {
            "responses": {
                "NotFound": {
                    "description": "Resource not found",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"}
                        }
                    }
                }
            }
        }

        responses = {
            "404": {
                "$ref": "#/responses/NotFound"
            }
        }

        parser = SwaggerParser()
        parser.spec = spec  # Set the spec for reference resolution
        parsed = parser._parse_responses(responses)

        assert parsed["404"].description == "Resource not found"
        assert parsed["404"].schema.properties["message"].type == "string"

    def test_no_schema_response(self):
        """Test parsing of responses without schemas (e.g., 204 No Content)."""
        responses = {
            "204": {
                "description": "Operation successful"
            }
        }

        parser = SwaggerParser()
        parsed = parser._parse_responses(responses)

        assert "204" in parsed
        assert parsed["204"].description == "Operation successful"
        assert parsed["204"].schema is None
