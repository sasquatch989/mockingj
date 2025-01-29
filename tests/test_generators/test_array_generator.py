"""Tests for Array Generator Strategy.

This module contains tests for verifying the correct generation of array data
according to various constraints in the MockingJ server.
"""
import pytest
from typing import List, Any

from mockingj.generators.array import ArrayGenerator
from mockingj.generators.base import DataGeneratorStrategy
from mockingj.models.schema import Schema
from mockingj.generators.exceptions import GeneratorError

# Error message constants
ERR_INVALID_ITEMS = "Invalid items specification"
ERR_INVALID_LENGTH = "Invalid array length constraints"
ERR_UNIQUE_CONSTRAINT = "Cannot generate unique items with given constraints"


class MockItemGenerator(DataGeneratorStrategy):
    """Mock generator for array items."""

    def __init__(self, values: List[Any]):
        self.values = values
        self.index = 0

    def generate(self, schema: Schema) -> Any:
        value = self.values[self.index]
        self.index = (self.index + 1) % len(self.values)
        return value


class TestArrayGenerator:
    """Test suite for array data generation strategy."""

    @pytest.fixture
    def generator(self):
        """Fixture providing an ArrayGenerator instance."""
        return ArrayGenerator(seed=12345)

    def test_basic_array_generation(self, generator):
        """Test generation of basic arrays with simple item types."""
        test_cases = [
            (Schema(type="string"), str),
            (Schema(type="integer"), int),
            (Schema(type="number"), float),
            (Schema(type="boolean"), bool)
        ]

        for item_schema, expected_type in test_cases:
            schema = Schema(
                type="array",
                items=item_schema,
                minItems=2,
                maxItems=5
            )
            result = generator.generate(schema)

            assert isinstance(result, list)
            assert 2 <= len(result) <= 5
            assert all(isinstance(item, expected_type) for item in result)

    def test_array_length_constraints(self, generator):
        """Test array generation with various length constraints."""
        test_cases = [
            (0, 5),  # Variable length
            (3, 3),  # Fixed length
            (0, 0),  # Empty array
            (10, 15)  # Longer array
        ]

        for min_items, max_items in test_cases:
            schema = Schema(
                type="array",
                items=Schema(type="string"),
                minItems=min_items,
                maxItems=max_items
            )
            result = generator.generate(schema)

            assert isinstance(result, list)
            assert min_items <= len(result) <= max_items

    def test_unique_items_constraint(self, generator):
        """Test generation of arrays with uniqueItems constraint."""
        # Test with simple types
        schema = Schema(
            type="array",
            items=Schema(type="integer", minimum=1, maximum=10),
            minItems=5,
            maxItems=5,
            uniqueItems=True
        )
        result = generator.generate(schema)

        assert len(result) == 5
        assert len(set(result)) == 5  # All items should be unique
        assert all(1 <= x <= 10 for x in result)

        # Test with objects
        object_schema = Schema(
            type="array",
            items=Schema(
                type="object",
                properties={
                    "id": Schema(type="integer", minimum=1, maximum=5),
                    "name": Schema(type="string")
                },
                required=["id"]
            ),
            minItems=3,
            uniqueItems=True
        )
        object_result = generator.generate(object_schema)

        # Check uniqueness by id
        ids = [item["id"] for item in object_result]
        assert len(ids) == len(set(ids))

    def test_tuple_validation(self, generator):
        """Test generation of tuple-style arrays with heterogeneous types."""
        schema = Schema(
            type="array",
            items=[
                Schema(type="string"),
                Schema(type="integer"),
                Schema(type="boolean")
            ],
            additionalItems=False  # Strict tuple length
        )
        result = generator.generate(schema)

        assert len(result) == 3
        assert isinstance(result[0], str)
        assert isinstance(result[1], int)
        assert isinstance(result[2], bool)

    def test_nested_arrays(self, generator):
        """Test generation of nested array structures."""
        schema = Schema(
            type="array",
            items=Schema(
                type="array",
                items=Schema(type="integer"),
                minItems=2,
                maxItems=3
            ),
            minItems=2,
            maxItems=4
        )
        result = generator.generate(schema)

        assert isinstance(result, list)
        assert 2 <= len(result) <= 4
        assert all(isinstance(subarray, list) for subarray in result)
        assert all(2 <= len(subarray) <= 3 for subarray in result)
        assert all(isinstance(item, int)
                   for subarray in result
                   for item in subarray)

    def test_array_with_object_items(self, generator):
        """Test generation of arrays containing object items."""
        schema = Schema(
            type="array",
            items=Schema(
                type="object",
                properties={
                    "id": Schema(type="integer"),
                    "name": Schema(type="string"),
                    "active": Schema(type="boolean")
                },
                required=["id", "name"]
            ),
            minItems=2,
            maxItems=5
        )
        result = generator.generate(schema)

        assert isinstance(result, list)
        assert 2 <= len(result) <= 5
        for item in result:
            assert isinstance(item, dict)
            assert "id" in item
            assert "name" in item
            assert isinstance(item["id"], int)
            assert isinstance(item["name"], str)

    @pytest.mark.parametrize("invalid_schema,expected_error", [
        (
                Schema(type="array", items=None),
                ERR_INVALID_ITEMS
        ),
        (
                Schema(type="array", minItems=10, maxItems=5),
                ERR_INVALID_LENGTH
        ),
        (
                Schema(
                    type="array",
                    items=Schema(type="integer", minimum=1, maximum=2),
                    minItems=5,
                    uniqueItems=True
                ),
                ERR_UNIQUE_CONSTRAINT
        )
    ])
    def test_invalid_constraints(self, generator, invalid_schema: Schema,
                                 expected_error: str):
        """Test handling of invalid array constraints."""
        with pytest.raises(GeneratorError, match=expected_error):
            generator.generate(invalid_schema)

    def test_consistent_generation(self, generator):
        """Test consistency of generated arrays with same seed."""
        schema = Schema(
            type="array",
            items=Schema(type="integer", minimum=1, maximum=100),
            minItems=5,
            maxItems=5
        )

        # Same schema should generate same result with same seed
        result1 = generator.generate(schema)
        result2 = generator.generate(schema)
        assert result1 == result2

        # Different seeds should generate different results
        generator2 = ArrayGenerator(seed=67890)
        result3 = generator2.generate(schema)
        assert result1 != result3
