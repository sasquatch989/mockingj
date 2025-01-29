"""Tests for Schema Models.

This module contains tests for verifying the behavior and validation of
schema models used for OpenAPI/Swagger specification parsing.
"""
import pytest
from typing import Any, Dict, Optional
from pydantic import ValidationError

from mockingj.models.schema import (
    Schema,
    StringFormat,
    NumberFormat,
    ArraySchema,
    ObjectSchema,
    PropertySchema
)


class TestBaseSchema:
    """Test suite for base schema functionality."""

    def test_schema_type_validation(self):
        """Test validation of schema types."""
        valid_types = ["string", "number", "integer", "boolean",
                       "array", "object", "null"]

        for schema_type in valid_types:
            schema = Schema(type=schema_type)
            assert schema.type == schema_type

        # Invalid type
        with pytest.raises(ValidationError, match="Invalid schema type"):
            Schema(type="invalid_type")

    def test_schema_nullable(self):
        """Test nullable property handling."""
        # Explicit nullable
        schema = Schema(type="string", nullable=True)
        assert schema.nullable is True

        # Default not nullable
        default_schema = Schema(type="string")
        assert default_schema.nullable is False

    def test_schema_default_value(self):
        """Test default value handling."""
        # String default
        str_schema = Schema(type="string", default="test")
        assert str_schema.default == "test"

        # Number default
        num_schema = Schema(type="number", default=42.0)
        assert num_schema.default == 42.0

        # Boolean default
        bool_schema = Schema(type="boolean", default=True)
        assert bool_schema.default is True

        # Invalid default type
        with pytest.raises(ValidationError):
            Schema(type="string", default=123)  # Number for string

    def test_schema_description(self):
        """Test schema description handling."""
        schema = Schema(
            type="string",
            description="A test schema",
            title="Test",
            example="example value"
        )
        assert schema.description == "A test schema"
        assert schema.title == "Test"
        assert schema.example == "example value"

    def test_schema_reference(self):
        """Test schema reference handling."""
        ref_schema = Schema(ref="#/definitions/TestSchema")
        assert ref_schema.ref == "#/definitions/TestSchema"
        assert ref_schema.type is None  # Type not required with ref

        # Cannot have both ref and type
        with pytest.raises(ValidationError):
            Schema(ref="#/definitions/TestSchema", type="string")


class TestStringSchema:
    """Test suite for string schema validation."""

    def test_string_format_validation(self):
        """Test validation of string formats."""
        valid_formats = [
            "date", "date-time", "password", "byte", "binary",
            "email", "uuid", "uri", "hostname", "ipv4", "ipv6"
        ]

        for format_type in valid_formats:
            schema = Schema(type="string", format=format_type)
            assert schema.format == format_type

        # Invalid format
        with pytest.raises(ValidationError):
            Schema(type="string", format="invalid_format")

    def test_string_length_constraints(self):
        """Test string length constraints."""
        schema = Schema(
            type="string",
            minLength=5,
            maxLength=10
        )
        assert schema.minLength == 5
        assert schema.maxLength == 10

        # Invalid length constraints
        with pytest.raises(ValidationError):
            Schema(type="string", minLength=-1)  # Negative length

        with pytest.raises(ValidationError):
            Schema(type="string", minLength=10, maxLength=5)  # min > max

    def test_string_pattern(self):
        """Test string pattern validation."""
        # Valid pattern
        schema = Schema(type="string", pattern="^[A-Z]{3}[0-9]{3}$")
        assert schema.pattern == "^[A-Z]{3}[0-9]{3}$"

        # Invalid pattern
        with pytest.raises(ValidationError):
            Schema(type="string", pattern="[")  # Invalid regex

    def test_string_enum(self):
        """Test string enum validation."""
        schema = Schema(
            type="string",
            enum=["red", "green", "blue"]
        )
        assert schema.enum == ["red", "green", "blue"]

        # Duplicate values not allowed
        with pytest.raises(ValidationError):
            Schema(type="string", enum=["red", "red", "blue"])


class TestNumberSchema:
    """Test suite for number schema validation."""

    def test_number_format_validation(self):
        """Test validation of number formats."""
        # Integer formats
        schema_int32 = Schema(type="integer", format="int32")
        assert schema_int32.format == "int32"

        schema_int64 = Schema(type="integer", format="int64")
        assert schema_int64.format == "int64"

        # Float formats
        schema_float = Schema(type="number", format="float")
        assert schema_float.format == "float"

        schema_double = Schema(type="number", format="double")
        assert schema_double.format == "double"

    def test_number_range_constraints(self):
        """Test numeric range constraints."""
        schema = Schema(
            type="number",
            minimum=0,
            maximum=100,
            exclusiveMinimum=True,
            exclusiveMaximum=False
        )
        assert schema.minimum == 0
        assert schema.maximum == 100
        assert schema.exclusiveMinimum is True
        assert schema.exclusiveMaximum is False

        # Invalid ranges
        with pytest.raises(ValidationError):
            Schema(type="number", minimum=100, maximum=0)

    def test_number_multiple_of(self):
        """Test multipleOf constraint."""
        schema = Schema(type="number", multipleOf=0.5)
        assert schema.multipleOf == 0.5

        # Invalid multipleOf
        with pytest.raises(ValidationError):
            Schema(type="number", multipleOf=0)  # Cannot be zero

        with pytest.raises(ValidationError):
            Schema(type="number", multipleOf=-1)  # Cannot be negative
