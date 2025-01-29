"""Tests for String Generator Strategy.

This module contains tests for verifying the correct generation of string data
according to various formats and constraints in the MockingJ server.
"""
import re
from typing import Any, Dict

import pytest

from mockingj.generators.string import StringGenerator
from mockingj.models.schema import Schema
from mockingj.generators.exceptions import GeneratorError

# Error message constants
ERR_INVALID_FORMAT = "Unsupported string format"
ERR_INVALID_PATTERN = "Invalid regular expression pattern"
ERR_LENGTH_CONSTRAINT = "Invalid length constraints"


class TestStringGenerator:
    """Test suite for string data generation strategy."""

    @pytest.fixture
    def generator(self):
        """Fixture providing a StringGenerator instance."""
        return StringGenerator(seed=12345)

    def test_basic_string_generation(self, generator):
        """Test generation of basic strings."""
        schema = Schema(type="string")
        result = generator.generate(schema)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("format,pattern", [
        ("email", r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
        ("date-time", r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"),
        ("date", r"^\d{4}-\d{2}-\d{2}$"),
        ("uri", r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$"),
        ("uuid", r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"),
        ("hostname", r"^[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]$"),
        ("ipv4", r"^(\d{1,3}\.){3}\d{1,3}$"),
        ("password", r"^[A-Za-z\d@$!%*#?&]{8,}$")
    ])
    def test_formatted_string_generation(self, generator, format: str,
                                         pattern: str):
        """Test generation of formatted strings."""
        schema = Schema(type="string", format=format)
        result = generator.generate(schema)

        assert re.match(pattern, result) is not None

        # Additional format-specific validations
        if format == "email":
            assert "." in result.split("@")[1]  # Domain has at least one dot
        elif format in ["date-time", "date"]:
            # Basic date validation (this is simplified)
            parts = result.replace("T", "-").replace(":", "-").replace("Z", "").split("-")
            assert all(part.isdigit() for part in parts)
        elif format == "ipv4":
            # Validate IP address ranges
            octets = [int(p) for p in result.split(".")]
            assert all(0 <= octet <= 255 for octet in octets)
        elif format == "password":
            # Check password complexity
            assert any(c.isupper() for c in result)
            assert any(c.islower() for c in result)
            assert any(c.isdigit() for c in result)
            assert any(c in "@$!%*#?&" for c in result)

    def test_length_constraints(self, generator):
        """Test string generation with length constraints."""
        schema = Schema(type="string", minLength=5, maxLength=10)
        result = generator.generate(schema)

        assert 5 <= len(result) <= 10

        # Test exact length
        exact_schema = Schema(type="string", minLength=7, maxLength=7)
        exact_result = generator.generate(exact_schema)

        assert len(exact_result) == 7

    def test_pattern_string_generation(self, generator):
        """Test generation of pattern-based strings."""
        test_patterns = [
            (r"^[A-Z]{3}\d{3}$", 6),  # Format like 'ABC123'
            (r"^(foo|bar|baz)$", None),  # One of specified words
            (r"^[\w\.-]+@[\w\.-]+$", None),  # Simple email-like pattern
            (r"^#[0-9a-fA-F]{6}$", 7)  # Hex color code
        ]

        for pattern, expected_length in test_patterns:
            schema = Schema(type="string", pattern=pattern)
            result = generator.generate(schema)

            assert re.match(pattern, result) is not None
            if expected_length:
                assert len(result) == expected_length

    def test_enum_string_generation(self, generator):
        """Test generation of enum strings."""
        test_cases = [
            (["red", "blue", "green"], "color"),
            (["GET", "POST", "PUT", "DELETE"], "http_method"),
            (["pending", "active", "completed"], "status"),
            (["xs", "sm", "md", "lg", "xl"], "size")
        ]

        for enum_values, name in test_cases:
            schema = Schema(type="string", enum=enum_values)
            result = generator.generate(schema)

            assert result in enum_values

            # Test multiple generations to ensure all values are possible
            results = set(generator.generate(schema) for _ in range(50))
            assert results.issubset(set(enum_values))
            assert len(results) > 1  # Should get different values

    def test_string_format_combination(self, generator):
        """Test string generation with combined constraints."""
        schema = Schema(
            type="string",
            format="email",
            pattern=r"^[a-zA-Z0-9._%+-]+@example\.(com|org|net)$",
            maxLength=30
        )
        result = generator.generate(schema)

        assert "@example." in result
        assert result.split("@example.")[1] in ["com", "org", "net"]
        assert len(result) <= 30
        assert re.match(schema.pattern, result) is not None

    @pytest.mark.parametrize("invalid_schema,expected_error", [
        (
                Schema(type="string", format="invalid_format"),
                ERR_INVALID_FORMAT
        ),
        (
                Schema(type="string", pattern="[invalid"),
                ERR_INVALID_PATTERN
        ),
        (
                Schema(type="string", minLength=10, maxLength=5),
                ERR_LENGTH_CONSTRAINT
        )
    ])
    def test_invalid_constraints(self, generator, invalid_schema: Schema,
                                 expected_error: str):
        """Test handling of invalid string constraints."""
        with pytest.raises(GeneratorError, match=expected_error):
            generator.generate(invalid_schema)

    def test_consistent_generation(self, generator):
        """Test consistency of generated strings with same seed."""
        schema = Schema(type="string", format="email")

        # Same schema should generate same result with same seed
        result1 = generator.generate(schema)
        result2 = generator.generate(schema)
        assert result1 == result2

        # Different seeds should generate different results
        generator2 = StringGenerator(seed=67890)
        result3 = generator2.generate(schema)
        assert result1 != result3
        