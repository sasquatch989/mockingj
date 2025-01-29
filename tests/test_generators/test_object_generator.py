"""Tests for Object Generator Strategy.

This module contains tests for verifying the correct generation of object data
according to various constraints in the MockingJ server.
"""
import pytest
from typing import Dict, Any

from mockingj.generators.object import ObjectGenerator
from mockingj.models.schema import Schema
from mockingj.generators.exceptions import GeneratorError

# Error message constants
ERR_INVALID_PROPERTIES = "Invalid properties specification"
ERR_REQUIRED_FIELD = "Cannot generate required field"
ERR_INVALID_DEPENDENCY = "Invalid property dependency"
ERR_PATTERN_PROPERTY = "Invalid pattern property specification"


class TestObjectGenerator:
    """Test suite for object data generation strategy."""

    @pytest.fixture
    def generator(self):
        """Fixture providing an ObjectGenerator instance."""
        return ObjectGenerator(seed=12345)

    def test_basic_object_generation(self, generator):
        """Test generation of basic objects with simple properties."""
        # Test different property types
        schema = Schema(
            type="object",
            properties={
                "string_field": Schema(type="string"),
                "integer_field": Schema(type="integer"),
                "number_field": Schema(type="number"),
                "boolean_field": Schema(type="boolean")
            }
        )
        result = generator.generate(schema)

        assert isinstance(result, dict)
        assert isinstance(result.get("string_field"), str)
        assert isinstance(result.get("integer_field"), int)
        assert isinstance(result.get("number_field"), float)
        assert isinstance(result.get("boolean_field"), bool)

    def test_required_properties(self, generator):
        """Test generation of objects with required properties."""
        schema = Schema(
            type="object",
            properties={
                "id": Schema(type="integer"),
                "name": Schema(type="string"),
                "email": Schema(type="string", format="email"),
                "optional_field": Schema(type="string")
            },
            required=["id", "name", "email"]
        )
        result = generator.generate(schema)

        # Required fields must be present
        assert "id" in result
        assert "name" in result
        assert "email" in result
        # Optional field may or may not be present
        assert isinstance(result.get("optional_field", ""), str)

    def test_nested_objects(self, generator):
        """Test generation of nested object structures."""
        schema = Schema(
            type="object",
            properties={
                "user": Schema(
                    type="object",
                    properties={
                        "id": Schema(type="integer"),
                        "contact": Schema(
                            type="object",
                            properties={
                                "email": Schema(type="string", format="email"),
                                "phone": Schema(type="string")
                            },
                            required=["email"]
                        )
                    },
                    required=["id", "contact"]
                )
            }
        )
        result = generator.generate(schema)

        assert "user" in result
        assert "id" in result["user"]
        assert "contact" in result["user"]
        assert "email" in result["user"]["contact"]
        assert "@" in result["user"]["contact"]["email"]

    def test_pattern_properties(self, generator):
        """Test generation of objects with pattern properties."""
        schema = Schema(
            type="object",
            patternProperties={
                "^str_": Schema(type="string"),
                "^num_": Schema(type="number"),
                "^bool_": Schema(type="boolean")
            },
            minProperties=3,
            maxProperties=6
        )
        result = generator.generate(schema)

        # Verify number of properties
        assert 3 <= len(result) <= 6

        # Verify property names and types match patterns
        for key, value in result.items():
            if key.startswith("str_"):
                assert isinstance(value, str)
            elif key.startswith("num_"):
                assert isinstance(value, (int, float))
            elif key.startswith("bool_"):
                assert isinstance(value, bool)

    def test_additional_properties(self, generator):
        """Test generation of objects with additionalProperties constraint."""
        # Test with additionalProperties as schema
        schema = Schema(
            type="object",
            properties={
                "id": Schema(type="integer")
            },
            additionalProperties=Schema(type="string"),
            minProperties=3
        )
        result = generator.generate(schema)

        assert len(result) >= 3
        assert isinstance(result["id"], int)
        # All additional properties should be strings
        additional_props = {k: v for k, v in result.items() if k != "id"}
        assert all(isinstance(v, str) for v in additional_props.values())

        # Test with additionalProperties=False
        strict_schema = Schema(
            type="object",
            properties={
                "id": Schema(type="integer"),
                "name": Schema(type="string")
            },
            additionalProperties=False
        )
        strict_result = generator.generate(strict_schema)

        assert set(strict_result.keys()).issubset({"id", "name"})

    def test_property_dependencies(self, generator):
        """Test generation of objects with property dependencies."""
        schema = Schema(
            type="object",
            properties={
                "credit_card": Schema(type="string"),
                "billing_address": Schema(type="string"),
                "shipping_address": Schema(type="string")
            },
            dependencies={
                "credit_card": ["billing_address"],
                "shipping_address": ["billing_address"]
            }
        )
        result = generator.generate(schema)

        # If dependent properties exist, their dependencies must exist
        if "credit_card" in result:
            assert "billing_address" in result
        if "shipping_address" in result:
            assert "billing_address" in result

    def test_property_constraints(self, generator):
        """Test generation with property count constraints."""
        schema = Schema(
            type="object",
            properties={
                "field1": Schema(type="string"),
                "field2": Schema(type="string"),
                "field3": Schema(type="string"),
                "field4": Schema(type="string"),
                "field5": Schema(type="string")
            },
            minProperties=2,
            maxProperties=4
        )
        result = generator.generate(schema)

        assert 2 <= len(result) <= 4
        assert all(isinstance(v, str) for v in result.values())

    @pytest.mark.parametrize("invalid_schema,expected_error", [
        (
                Schema(
                    type="object",
                    properties={"field": None}
                ),
                ERR_INVALID_PROPERTIES
        ),
        (
                Schema(
                    type="object",
                    properties={
                        "card": Schema(type="string")
                    },
                    required=["missing_field"]
                ),
                ERR_REQUIRED_FIELD
        ),
        (
                Schema(
                    type="object",
                    dependencies={
                        "field1": "invalid_dependency"
                    }
                ),
                ERR_INVALID_DEPENDENCY
        ),
        (
                Schema(
                    type="object",
                    patternProperties={
                        "[": Schema(type="string")  # Invalid regex
                    }
                ),
                ERR_PATTERN_PROPERTY
        )
    ])
    def test_invalid_constraints(self, generator, invalid_schema: Schema,
                                 expected_error: str):
        """Test handling of invalid object constraints."""
        with pytest.raises(GeneratorError, match=expected_error):
            generator.generate(invalid_schema)

    def test_consistent_generation(self, generator):
        """Test consistency of generated objects with same seed."""
        schema = Schema(
            type="object",
            properties={
                "id": Schema(type="integer"),
                "name": Schema(type="string"),
                "active": Schema(type="boolean")
            },
            required=["id", "name"]
        )

        # Same schema should generate same result with same seed
        result1 = generator.generate(schema)
        result2 = generator.generate(schema)
        assert result1 == result2

        # Different seeds should generate different results
        generator2 = ObjectGenerator(seed=67890)
        result3 = generator2.generate(schema)
        assert result1 != result3
