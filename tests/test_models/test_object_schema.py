"""Tests for Object Schema Models.

This module contains tests for verifying the behavior and validation of
object schema models used in the MockingJ server.

File path: tests/test_models/test_object_schema.py
"""
import pytest
from typing import Dict, Any
from pydantic import ValidationError

from mockingj.models.schema import (
    Schema,
    ObjectSchema,
    PropertySchema
)


class TestObjectSchema:
    """Test suite for object schema validation.

    Organized in sections:
    1. Basic property validation
    2. Required fields handling
    3. Additional properties
    4. Pattern properties
    5. Property dependencies
    6. Complex nested structures
    """

    def test_basic_object_properties(self):
        """Test basic object schema property definition and validation.

        Verifies:
        - Simple property types
        - Property names
        - Default property values
        """
        schema = ObjectSchema(
            type="object",
            properties={
                "string_prop": Schema(type="string"),
                "integer_prop": Schema(type="integer"),
                "number_prop": Schema(type="number"),
                "boolean_prop": Schema(type="boolean")
            }
        )

        assert schema.type == "object"
        assert len(schema.properties) == 4
        assert schema.properties["string_prop"].type == "string"
        assert schema.properties["integer_prop"].type == "integer"
        assert schema.properties["boolean_prop"].type == "boolean"

        # Test with property having default value
        schema_with_default = ObjectSchema(
            type="object",
            properties={
                "status": Schema(type="string", default="active")
            }
        )
        assert schema_with_default.properties["status"].default == "active"

    def test_required_properties(self):
        """Test required property validation and constraints.

        Verifies:
        - Required property lists
        - Validation of required vs optional properties
        - Error cases for missing required properties
        """
        schema = ObjectSchema(
            type="object",
            properties={
                "id": Schema(type="integer"),
                "name": Schema(type="string"),
                "description": Schema(type="string")
            },
            required=["id", "name"]
        )

        assert "id" in schema.required
        assert "name" in schema.required
        assert "description" not in schema.required

        # Test invalid required field reference
        with pytest.raises(ValidationError, match="Required property not found"):
            ObjectSchema(
                type="object",
                properties={"name": Schema(type="string")},
                required=["id"]  # id not in properties
            )

    def test_additional_properties(self):
        """Test additional properties handling.

        Verifies:
        - Boolean additionalProperties
        - Schema-based additionalProperties
        - Validation of additional property values
        """
        # Forbidden additional properties
        strict_schema = ObjectSchema(
            type="object",
            properties={"name": Schema(type="string")},
            additionalProperties=False
        )
        assert strict_schema.additionalProperties is False

        # Additional properties with schema
        flexible_schema = ObjectSchema(
            type="object",
            properties={"id": Schema(type="integer")},
            additionalProperties=Schema(type="string")
        )
        assert isinstance(flexible_schema.additionalProperties, Schema)
        assert flexible_schema.additionalProperties.type == "string"

    def test_pattern_properties(self):
        """Test pattern property validation and constraints.

        Verifies:
        - Pattern property regex validation
        - Pattern property schema validation
        - Multiple pattern properties
        """
        schema = ObjectSchema(
            type="object",
            patternProperties={
                "^S_": Schema(type="string"),
                "^I_": Schema(type="integer"),
                "^N_": Schema(type="number")
            }
        )

        assert len(schema.patternProperties) == 3
        assert schema.patternProperties["^S_"].type == "string"
        assert schema.patternProperties["^I_"].type == "integer"

        # Invalid pattern
        with pytest.raises(ValidationError, match="Invalid regex pattern"):
            ObjectSchema(
                type="object",
                patternProperties={"[": Schema(type="string")}
            )

    def test_property_dependencies(self):
        """Test property dependency validation.

        Verifies:
        - Property dependencies
        - Schema dependencies
        - Circular dependency prevention
        """
        schema = ObjectSchema(
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

        assert "billing_address" in schema.dependencies["credit_card"]
        assert "billing_address" in schema.dependencies["shipping_address"]

        # Schema dependency
        schema_with_dep = ObjectSchema(
            type="object",
            properties={"item": Schema(type="string")},
            dependencies={
                "item": Schema(
                    type="object",
                    properties={"quantity": Schema(type="integer")},
                    required=["quantity"]
                )
            }
        )
        assert isinstance(schema_with_dep.dependencies["item"], Schema)

    def test_nested_objects(self):
        """Test nested object schema validation.

        Verifies:
        - Multi-level object nesting
        - Complex property types
        - Nested required fields
        """
        schema = ObjectSchema(
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
                                "address": Schema(
                                    type="object",
                                    properties={
                                        "street": Schema(type="string"),
                                        "city": Schema(type="string"),
                                        "country": Schema(type="string")
                                    },
                                    required=["street", "country"]
                                )
                            },
                            required=["email"]
                        )
                    },
                    required=["id", "contact"]
                )
            }
        )

        assert schema.properties["user"].type == "object"
        assert "id" in schema.properties["user"].required
        assert "email" in schema.properties["user"].properties["contact"].required
        assert "street" in (schema.properties["user"].properties["contact"]
                            .properties["address"].required)

    def test_property_name_constraints(self):
        """Test property naming constraints and validation.

        Verifies:
        - Property name length limits
        - Property name patterns
        - Invalid property names
        """
        # Test maximum property name length
        long_name = "a" * 256
        with pytest.raises(ValidationError, match="Property name too long"):
            ObjectSchema(
                type="object",
                properties={long_name: Schema(type="string")}
            )

        # Test invalid property names
        invalid_names = ["", " ", "invalid.name", "invalid/name"]
        for name in invalid_names:
            with pytest.raises(ValidationError):
                ObjectSchema(
                    type="object",
                    properties={name: Schema(type="string")}
                )

    def test_property_count_constraints(self):
        """Test property count validation and constraints.

        Verifies:
        - Minimum properties constraint
        - Maximum properties constraint
        - Property count validation
        """
        schema = ObjectSchema(
            type="object",
            properties={
                "prop1": Schema(type="string"),
                "prop2": Schema(type="string"),
                "prop3": Schema(type="string")
            },
            minProperties=1,
            maxProperties=2
        )

        assert schema.minProperties == 1
        assert schema.maxProperties == 2

        # Invalid property counts
        with pytest.raises(ValidationError):
            ObjectSchema(
                type="object",
                properties={},
                minProperties=5,
                maxProperties=3
            )
