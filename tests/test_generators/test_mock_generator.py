"""Tests for Mock Data Generator.

This module contains tests for verifying the correct creation and coordination
of data generation strategies in the MockingJ server.
"""
import pytest
from typing import Any, Dict

from mockingj.generators.base import DataGeneratorStrategy
from mockingj.generators.mock_generator import MockDataGenerator
from mockingj.models.schema import Schema
from mockingj.utils.cache import CacheManager

# Error message constants
ERR_INVALID_TYPE = "Unsupported data type"
ERR_MISSING_SCHEMA = "Missing schema specification"
ERR_INVALID_FORMAT = "Unsupported data format"


class MockStrategy(DataGeneratorStrategy):
    """Mock strategy for testing."""
    def generate(self, schema: Schema) -> Any:
        return "test_value"


class TestMockDataGenerator:
    """Test suite for mock data generation coordination."""

    @pytest.fixture
    def mock_cache(self):
        """Fixture providing a mock cache manager."""
        return CacheManager()

    @pytest.fixture
    def generator(self, mock_cache):
        """Fixture providing a configured MockDataGenerator."""
        return MockDataGenerator(cache_manager=mock_cache)

    def test_generator_initialization(self, generator):
        """Test basic generator initialization."""
        assert generator is not None
        assert generator.cache_manager is not None
        assert len(generator.generators) > 0  # Should have default generators

    def test_register_custom_generator(self, generator):
        """Test registration of custom generator strategy."""
        mock_strategy = MockStrategy()
        generator.register_generator("custom", mock_strategy)

        schema = Schema(type="custom")
        result = generator.generate_data(schema)

        assert result == "test_value"

    def test_generate_string_data(self, generator):
        """Test generation of string data."""
        schema = Schema(type="string", format="email")
        result = generator.generate_data(schema)

        assert isinstance(result, str)
        assert "@" in result  # Basic email format validation

    def test_generate_number_data(self, generator):
        """Test generation of numeric data."""
        schema = Schema(type="integer", minimum=1, maximum=100)
        result = generator.generate_data(schema)

        assert isinstance(result, int)
        assert 1 <= result <= 100

    def test_generate_array_data(self, generator):
        """Test generation of array data."""
        schema = Schema(
            type="array",
            items=Schema(type="string"),
            minItems=1,
            maxItems=5
        )
        result = generator.generate_data(schema)

        assert isinstance(result, list)
        assert 1 <= len(result) <= 5
        assert all(isinstance(item, str) for item in result)

    def test_generate_object_data(self, generator):
        """Test generation of object data."""
        schema = Schema(
            type="object",
            properties={
                "id": Schema(type="integer"),
                "name": Schema(type="string")
            },
            required=["id"]
        )
        result = generator.generate_data(schema)

        assert isinstance(result, dict)
        assert "id" in result
        assert isinstance(result["id"], int)

    def test_consistent_generation(self, generator):
        """Test consistency of generated data with same schema and seed."""
        schema = Schema(type="string", format="email")

        result1 = generator.generate_data(schema)
        result2 = generator.generate_data(schema)

        assert result1 == result2  # Should be consistent with same seed

    def test_cache_usage(self, generator, mock_cache):
        """Test that generator uses cache appropriately."""
        schema = Schema(type="string")
        cache_key = generator._get_cache_key(schema)

        # First generation should cache
        result1 = generator.generate_data(schema)
        assert mock_cache.get_cached_value(cache_key) == result1

        # Second generation should use cache
        result2 = generator.generate_data(schema)
        assert result1 == result2

    @pytest.mark.parametrize("invalid_schema,expected_error", [
        (
            Schema(type="invalid_type"),
            ERR_INVALID_TYPE
        ),
        (
            Schema(type="string", format="invalid_format"),
            ERR_INVALID_FORMAT
        ),
        (
            None,
            ERR_MISSING_SCHEMA
        )
    ])
    def test_invalid_schemas(self, generator, invalid_schema: Schema,
                           expected_error: str):
        """Test handling of invalid schema specifications."""
        with pytest.raises(ValueError, match=expected_error):
            generator.generate_data(invalid_schema)

    def test_nested_object_generation(self, generator):
        """Test generation of nested object structures."""
        schema = Schema(
            type="object",
            properties={
                "user": Schema(
                    type="object",
                    properties={
                        "id": Schema(type="integer"),
                        "address": Schema(
                            type="object",
                            properties={
                                "street": Schema(type="string"),
                                "city": Schema(type="string")
                            },
                            required=["street"]
                        )
                    },
                    required=["id"]
                )
            }
        )

        result = generator.generate_data(schema)

        assert isinstance(result, dict)
        assert "user" in result
        assert "id" in result["user"]
        assert "address" in result["user"]
        assert "street" in result["user"]["address"]

    def test_generator_with_refs(self, generator):
        """Test generation with schema references."""
        ref_schema = Schema(
            type="object",
            properties={
                "name": Schema(type="string"),
                "age": Schema(type="integer", minimum=0)
            }
        )

        main_schema = Schema(
            type="array",
            items=Schema(ref=ref_schema)
        )

        result = generator.generate_data(main_schema)

        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)
        assert all("name" in item and "age" in item for item in result)
        assert all(isinstance(item["age"], int) and item["age"] >= 0
                  for item in result)
        