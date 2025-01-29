"""Tests for basic SwaggerParser functionality.

These tests cover the fundamental parsing capabilities of the SwaggerParser class,
including loading files, basic validation, and simple schema parsing.
"""
import json
from pathlib import Path

import pytest
from mockingj.parser.swagger import SwaggerParser
from mockingj.parser.exceptions import SwaggerParseError


class TestBasicParser:
    """Test basic functionality of the SwaggerParser."""

    def test_parser_loads_valid_file(self, sample_swagger_content, temp_dir):
        """Test that parser can load a valid swagger file."""
        # Arrange
        swagger_file = temp_dir / "swagger.json"
        swagger_file.write_text(json.dumps(sample_swagger_content))
        parser = SwaggerParser()

        # Act
        spec = parser.parse(swagger_file)

        # Assert
        assert spec.swagger == "2.0"
        assert spec.info.title == "Test API"
        assert spec.info.version == "1.0.0"
        assert "/test" in spec.paths

    def test_parser_validates_swagger_version(self, temp_dir):
        """Test that parser validates swagger version."""
        # Arrange
        invalid_content = {
            "swagger": "1.0",  # Invalid version
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {}
        }
        swagger_file = temp_dir / "invalid_swagger.json"
        swagger_file.write_text(json.dumps(invalid_content))
        parser = SwaggerParser()

        # Act/Assert
        with pytest.raises(SwaggerParseError, match="Unsupported Swagger version"):
            parser.parse(swagger_file)

    def test_parser_requires_info_section(self, temp_dir):
        """Test that parser requires info section."""
        # Arrange
        invalid_content = {
            "swagger": "2.0",
            "paths": {}  # Missing info section
        }
        swagger_file = temp_dir / "invalid_swagger.json"
        swagger_file.write_text(json.dumps(invalid_content))
        parser = SwaggerParser()

        # Act/Assert
        with pytest.raises(SwaggerParseError, match="Missing required 'info' section"):
            parser.parse(swagger_file)

    def test_parser_extracts_paths(self, sample_swagger_content, temp_dir):
        """Test that parser correctly extracts API paths."""
        # Arrange
        swagger_file = temp_dir / "swagger.json"
        swagger_file.write_text(json.dumps(sample_swagger_content))
        parser = SwaggerParser()

        # Act
        spec = parser.parse(swagger_file)
        paths = spec.get_paths()

        # Assert
        assert len(paths) == 1
        assert paths[0].path == "/test"
        assert paths[0].method == "get"
        assert "200" in paths[0].responses

    def test_path_parameters_extracted(self, temp_dir):
        """Test that parser extracts path parameters."""
        # Arrange
        content = {
            "swagger": "2.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users/{id}": {
                    "get": {
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "required": True,
                                "type": "string"
                            }
                        ],
                        "responses": {
                            "200": {"description": "OK"}
                        }
                    }
                }
            }
        }
        swagger_file = temp_dir / "swagger.json"
        swagger_file.write_text(json.dumps(content))
        parser = SwaggerParser()

        # Act
        spec = parser.parse(swagger_file)
        paths = spec.get_paths()

        # Assert
        assert len(paths) == 1
        assert paths[0].parameters[0].name == "id"
        assert paths[0].parameters[0].location == "path"
        assert paths[0].parameters[0].required is True

    def test_response_schema_extracted(self, sample_swagger_content, temp_dir):
        """Test that parser extracts response schemas."""
        # Arrange
        swagger_file = temp_dir / "swagger.json"
        swagger_file.write_text(json.dumps(sample_swagger_content))
        parser = SwaggerParser()

        # Act
        spec = parser.parse(swagger_file)
        paths = spec.get_paths()

        # Assert
        response_schema = paths[0].responses["200"].schema
        assert response_schema.type == "object"
        assert "message" in response_schema.properties
        assert response_schema.properties["message"].type == "string"
