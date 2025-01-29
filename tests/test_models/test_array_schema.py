"""Tests for Array Schema Models.

This module contains tests for verifying the behavior and validation of
array schema models used in the MockingJ server.

File path: tests/test_models/test_array_schema.py
"""
import pytest
from typing import List, Union, Dict, Any
from pydantic import ValidationError

from mockingj.models.schema import (
    Schema,
    ArraySchema
)

class TestArraySchema:
    """Test suite for array schema validation."""

    def test_basic_array_schema(self):
        """Test creation of basic array schemas with simple item types."""
        # Array of strings
        schema = ArraySchema(
            items=Schema(type="string")
        )
        assert schema.type == "array"
        assert schema.items.type == "string"
        assert schema.uniqueItems is False  # Default value

        # Array of integers
        num_schema = ArraySchema(
            items=Schema(type="integer", minimum=0)
        )
        assert num_schema.items.type == "integer"
        assert num_schema.items.minimum == 0

    def test_array_length_constraints(self):
        """Test array length constraint validation."""
        schema = ArraySchema(
            items=Schema(type="string"),
            minItems=1,
            maxItems=5
        )
        assert schema.minItems == 1
        assert schema.maxItems == 5

        # Invalid length constraints
        with pytest.raises(ValidationError, match="maxItems must be >= minItems"):
            ArraySchema(
                items=Schema(type="string"),
                minItems=5,
                maxItems=1
            )

        # Negative length constraints
        with pytest.raises(ValidationError):
            ArraySchema(
                items=Schema(type="string"),
                minItems=-1
            )

    def test_unique_items_constraint(self):
        """Test unique items constraint handling."""
        schema = ArraySchema(
            items=Schema(type="string"),
            uniqueItems=True
        )
        assert schema.uniqueItems is True

        # Test with default values
        schema_with_default = ArraySchema(
            items=Schema(type="string"),
            uniqueItems=True,
            default=["a", "b", "c"]
        )
        assert schema_with_default.default == ["a", "b", "c"]

        # Test invalid default with duplicates
        with pytest.raises(ValidationError):
            ArraySchema(
                items=Schema(type="string"),
                uniqueItems=True,
                default=["a", "a", "b"]
            )

    def test_tuple_validation(self):
        """Test validation of tuple-style arrays with fixed items."""
        schema = ArraySchema(
            items=[
                Schema(type="string"),
                Schema(type="integer"),
                Schema(type="boolean")
            ],
            additionalItems=False
        )
        assert len(schema.items) == 3
        assert schema.items[0].type == "string"
        assert schema.items[1].type == "integer"
        assert schema.items[2].type == "boolean"
        assert schema.additionalItems is False

    def test_nested_array_schema(self):
        """Test nested array schema validation."""
        schema = ArraySchema(
            items=ArraySchema(
                items=Schema(type="integer"),
                minItems=1
            ),
            minItems=2
        )
        assert schema.type == "array"
        assert isinstance(schema.items, ArraySchema)
        assert schema.items.type == "array"
        assert schema.items.items.type == "integer"
        assert schema.items.minItems == 1
        assert schema.minItems == 2

    def test_array_with_complex_items(self):
        """Test arrays with complex item schemas."""
        schema = ArraySchema(
            items=Schema(
                type="object",
                properties={
                    "id": Schema(type="integer"),
                    "name": Schema(type="string"),
                    "tags": ArraySchema(
                        items=Schema(type="string")
                    )
                },
                required=["id"]
            )
        )
        assert schema.items.type == "object"
        assert "id" in schema.items.required
        assert schema.items.properties["tags"].type == "array"
        assert schema.items.properties["tags"].items.type == "string"

    def test_array_default_values(self):
        """Test array schema default value handling."""
        schema = ArraySchema(
            items=Schema(type="string"),
            default=["item1", "item2"]
        )
        assert schema.default == ["item1", "item2"]

        # Invalid default value type
        with pytest.raises(ValidationError):
            ArraySchema(
                items=Schema(type="string"),
                default=[1, 2, 3]  # Numbers for string array
            )

    def test_array_examples(self):
        """Test array schema example handling."""
        schema = ArraySchema(
            items=Schema(type="number"),
            examples=[[1, 2, 3], [4, 5, 6]]
        )
        assert len(schema.examples) == 2
        assert schema.examples[0] == [1, 2, 3]
        assert schema.examples[1] == [4, 5, 6]

        # Invalid example values
        with pytest.raises(ValidationError):
            ArraySchema(
                items=Schema(type="number"),
                examples=[["a", "b", "c"]]  # Strings for number array
            )

    def test_array_contains_constraint(self):
        """Test array contains constraint validation."""
        schema = ArraySchema(
            items=Schema(type="string"),
            contains=Schema(
                type="string",
                pattern="^test-"
            ),
            minContains=1,
            maxContains=3
        )
        assert schema.contains.type == "string"
        assert schema.contains.pattern == "^test-"
        assert schema.minContains == 1
        assert schema.maxContains == 3

        # Invalid contains constraints
        with pytest.raises(ValidationError):
            ArraySchema(
                items=Schema(type="string"),
                contains=Schema(type="string"),
                minContains=3,
                maxContains=1
            )
