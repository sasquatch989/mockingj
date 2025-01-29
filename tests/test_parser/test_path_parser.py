"""Tests for Path Parsing functionality.

This module contains tests for verifying the correct parsing and validation
of Swagger/OpenAPI path definitions.
"""
import pytest
from typing import Dict, Any

from mockingj.parser.swagger import SwaggerParser
from mockingj.parser.exceptions import PathValidationError, InvalidMethodError

# Error message constants
ERR_INVALID_PATH = "Invalid path specification"
ERR_INVALID_METHOD = "Invalid HTTP method"

class TestPathParser:
    """Test suite for path parsing functionality."""

    def test_parse_basic_path(self):
        """Test parsing of basic path with single method."""
        path_spec = {
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

        parser = SwaggerParser()
        paths = parser._parse_paths(path_spec)

        assert "/test" in paths
        assert "get" in paths["/test"]
        assert "200" in paths["/test"]["get"].responses

    def test_multiple_methods_same_path(self):
        """Test parsing multiple HTTP methods for same path."""
        path_spec = {
            "/resource": {
                "get": {
                    "responses": {"200": {"description": "Success"}}
                },
                "post": {
                    "responses": {"201": {"description": "Created"}}
                },
                "delete": {
                    "responses": {"204": {"description": "Deleted"}}
                }
            }
        }

        parser = SwaggerParser()
        paths = parser._parse_paths(path_spec)

        assert all(method in paths["/resource"]
                  for method in ["get", "post", "delete"])
        assert "200" in paths["/resource"]["get"].responses
        assert "201" in paths["/resource"]["post"].responses
        assert "204" in paths["/resource"]["delete"].responses

    def test_parse_path_parameters(self):
        """Test parsing of path parameters."""
        path_spec = {
            "/users/{id}": {
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "type": "string"
                    }
                ],
                "get": {
                    "responses": {
                        "200": {
                            "description": "User found"
                        }
                    }
                }
            }
        }

        parser = SwaggerParser()
        paths = parser._parse_paths(path_spec)

        assert "/users/{id}" in paths
        params = paths["/users/{id}"].parameters
        assert len(params) == 1
        assert params[0].name == "id"
        assert params[0].location == "path"
        assert params[0].required is True

    @pytest.mark.parametrize("invalid_path,expected_error", [
        ({"/test{}": {}}, ERR_INVALID_PATH),  # Invalid path template
        ({"/test": {"invalid": {}}}, ERR_INVALID_METHOD),  # Invalid HTTP method
        ({"/": {}}, ERR_INVALID_PATH),  # Empty path
    ])
    def test_invalid_path_specifications(self, invalid_path: Dict[str, Any],
                                       expected_error: str):
        """Test handling of invalid path specifications."""
        parser = SwaggerParser()
        with pytest.raises(PathValidationError, match=expected_error):
            parser._parse_paths(invalid_path)

    def test_duplicate_parameter_names(self):
        """Test validation of duplicate parameter names."""
        path_spec = {
            "/test/{id}": {
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "type": "string"
                    },
                    {
                        "name": "id",  # Duplicate name
                        "in": "query",
                        "type": "string"
                    }
                ],
                "get": {
                    "responses": {"200": {"description": "Success"}}
                }
            }
        }

        parser = SwaggerParser()
        with pytest.raises(PathValidationError,
                         match="Duplicate parameter name: id"):
            parser._parse_paths(path_spec)
