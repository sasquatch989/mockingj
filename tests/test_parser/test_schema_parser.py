"""Tests for Schema Parsing functionality.

This module contains tests for verifying the correct parsing and validation
of Swagger/OpenAPI schema definitions.
"""
import pytest
from typing import Dict, Any

from mockingj.parser.swagger import SwaggerParser
from mockingj.parser.exceptions import (
    SchemaValidationError,
    InvalidReferenceError,
    CircularReferenceError
)

# Error message constants
ERR_INVALID_TYPE = "Invalid type specification"
ERR_CIRCULAR_REF = "Circular reference detected"
ERR_INVALID_REF = "Invalid reference"
ERR_INVALID_FORMAT = "Invalid format specification"


class TestSchemaParser:
    """Test suite for schema parsing functionality."""

    def test_parse_primitive_types(self, sample_openapi_types):
        """Test parsing of primitive data types."""
        parser = SwaggerParser()

        # Test string type
        string_schema = sample_openapi_types["string"]
        parsed_string = parser._parse_schema(string_schema)
        assert parsed_string.type == "string"
        assert parsed_string.format == "email"
        assert parsed_string.max_length == 100
        assert parsed_string.min_length == 1

        # Test integer type
        integer_schema = sample_openapi_types["integer"]
        parsed_integer = parser._parse_schema(integer_schema)
        assert parsed_integer.type == "integer"
        assert parsed_integer.format == "int64"
        assert parsed_integer.maximum == 100
        assert parsed_integer.minimum == 1

    def test_parse_array_type(self, sample_openapi_types):
        """Test parsing of array types."""
        parser = SwaggerParser()
        array_schema = sample_openapi_types["array"]
        parsed_array = parser._parse_schema(array_schema)

        assert parsed_array.type == "array"
        assert parsed_array.max_items == 5
        assert parsed_array.min_items == 1
        assert parsed_array.items.type == "string"

    def test_parse_object_type(self, sample_openapi_types):
        """Test parsing of object types."""
        parser = SwaggerParser()
        object_schema = sample_openapi_types["object"]
        parsed_object = parser._parse_schema(object_schema)

        assert parsed_object.type == "object"
        assert "id" in parsed_object.properties
        assert "name" in parsed_object.properties
        assert "id" in parsed_object.required
        assert parsed_object.properties["id"].type == "integer"
        assert parsed_object.properties["name"].type == "string"

    def test_parse_nested_objects(self):
        """Test parsing of nested object structures."""
        nested_schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "address": {
                            "type": "object",
                            "properties": {
                                "street": {"type": "string"},
                                "city": {"type": "string"}
                            },
                            "required": ["street"]
                        }
                    },
                    "required": ["id"]
                }
            }
        }

        parser = SwaggerParser()
        parsed = parser._parse_schema(nested_schema)

        assert parsed.type == "object"
        assert parsed.properties["user"].type == "object"
        assert parsed.properties["user"].properties["address"].type == "object"
        assert "street" in parsed.properties["user"].properties["address"].required

    def test_invalid_type_specification(self):
        """Test handling of invalid type specifications."""
        invalid_schema = {
            "type": "invalid_type",
            "properties": {}
        }

        parser = SwaggerParser()
        with pytest.raises(SchemaValidationError, match=ERR_INVALID_TYPE):
            parser._parse_schema(invalid_schema)

    def test_invalid_format_specification(self):
        """Test handling of invalid format specifications."""
        invalid_schema = {
            "type": "string",
            "format": "invalid_format"
        }

        parser = SwaggerParser()
        with pytest.raises(SchemaValidationError, match=ERR_INVALID_FORMAT):
            parser._parse_schema(invalid_schema)

    @pytest.mark.parametrize("schema,expected_error", [
        ({"$ref": "#/invalid/path"}, ERR_INVALID_REF),
        ({"$ref": "#/definitions/undefined"}, ERR_INVALID_REF),
    ])
    def test_invalid_references(self, schema: Dict[str, Any], expected_error: str):
        """Test handling of invalid references."""
        parser = SwaggerParser()
        with pytest.raises(InvalidReferenceError, match=expected_error):
            parser._parse_schema(schema)

    def test_circular_reference_detection(self):
        """Test detection of circular references in schemas."""
        circular_schema = {
            "definitions": {
                "Person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "friend": {"$ref": "#/definitions/Person"}
                    }
                }
            }
        }

        parser = SwaggerParser()
        with pytest.raises(CircularReferenceError, match=ERR_CIRCULAR_REF):
            parser._parse_schema({"$ref": "#/definitions/Person"}, circular_schema)

    def test_additional_properties(self):
        """Test parsing of additionalProperties specification."""
        schema = {
            "type": "object",
            "additionalProperties": {
                "type": "string"
            }
        }

        parser = SwaggerParser()
        parsed = parser._parse_schema(schema)

        assert parsed.type == "object"
        assert parsed.additional_properties.type == "string"

    def test_schema_with_enums(self):
        """Test parsing of enum specifications."""
        schema = {
            "type": "string",
            "enum": ["pending", "active", "deleted"]
        }

        parser = SwaggerParser()
        parsed = parser._parse_schema(schema)

        assert parsed.type == "string"
        assert parsed.enum == ["pending", "active", "deleted"]

    def test_allof_schema(self):
        """Test parsing of allOf specifications."""
        schema = {
            "allOf": [
                {"type": "object", "properties": {"name": {"type": "string"}}},
                {"type": "object", "properties": {"age": {"type": "integer"}}}
            ]
        }

        parser = SwaggerParser()
        parsed = parser._parse_schema(schema)

        assert "name" in parsed.properties
        assert "age" in parsed.properties
        assert parsed.properties["name"].type == "string"
        assert parsed.properties["age"].type == "integer"
