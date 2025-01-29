"""Tests for Number Generator Strategy.

This module contains tests for verifying the correct generation of numeric data
according to various constraints in the MockingJ server.
"""
import pytest
from decimal import Decimal

from mockingj.generators.number import NumberGenerator
from mockingj.models.schema import Schema
from mockingj.generators.exceptions import GeneratorError

# Error message constants
ERR_INVALID_BOUNDS = "Invalid numeric bounds"
ERR_INVALID_MULTIPLE = "Invalid multipleOf value"
ERR_INVALID_FORMAT = "Unsupported number format"


class TestNumberGenerator:
    """Test suite for numeric data generation strategy."""

    @pytest.fixture
    def generator(self):
        """Fixture providing a NumberGenerator instance."""
        return NumberGenerator(seed=12345)

    def test_basic_integer_generation(self, generator):
        """Test generation of basic integers."""
        schema = Schema(type="integer")
        result = generator.generate(schema)

        assert isinstance(result, int)
        # Default bounds should apply
        assert -2 ** 31 <= result <= 2 ** 31 - 1

    def test_basic_number_generation(self, generator):
        """Test generation of basic floating point numbers."""
        schema = Schema(type="number")
        result = generator.generate(schema)

        assert isinstance(result, float)
        assert -1e6 <= result <= 1e6  # Default bounds

    @pytest.mark.parametrize("format,expected_type,min_val,max_val", [
        ("int32", int, -2 ** 31, 2 ** 31 - 1),
        ("int64", int, -2 ** 63, 2 ** 63 - 1),
        ("float", float, -3.4e38, 3.4e38),
        ("double", float, -1.8e308, 1.8e308)
    ])
    def test_number_formats(self, generator, format, expected_type,
                            min_val, max_val):
        """Test generation of numbers with different formats."""
        schema = Schema(type="number", format=format)
        result = generator.generate(schema)

        assert isinstance(result, expected_type)
        assert min_val <= result <= max_val

    def test_bounded_integer_generation(self, generator):
        """Test generation of integers with bounds."""
        test_cases = [
            (0, 100),  # Small positive range
            (-50, 50),  # Range crossing zero
            (1000, 1100),  # Large numbers
            (5, 5)  # Single value
        ]

        for minimum, maximum in test_cases:
            schema = Schema(
                type="integer",
                minimum=minimum,
                maximum=maximum
            )
            result = generator.generate(schema)

            assert isinstance(result, int)
            assert minimum <= result <= maximum

    def test_bounded_float_generation(self, generator):
        """Test generation of floating point numbers with bounds."""
        test_cases = [
            (0.0, 1.0),  # Standard unit interval
            (-1.0, 1.0),  # Symmetric around zero
            (0.1, 0.2),  # Small range
            (1000.0, 1001.0)  # Large numbers
        ]

        for minimum, maximum in test_cases:
            schema = Schema(
                type="number",
                minimum=minimum,
                maximum=maximum
            )
            result = generator.generate(schema)

            assert isinstance(result, float)
            assert minimum <= result <= maximum

    def test_exclusive_bounds(self, generator):
        """Test generation with exclusive bounds."""
        schema = Schema(
            type="number",
            minimum=0,
            maximum=10,
            exclusiveMinimum=True,
            exclusiveMaximum=True
        )
        result = generator.generate(schema)

        assert 0 < result < 10

        # Test with integers
        int_schema = Schema(
            type="integer",
            minimum=5,
            maximum=10,
            exclusiveMinimum=True,
            exclusiveMaximum=True
        )
        int_result = generator.generate(int_schema)

        assert isinstance(int_result, int)
        assert 5 < int_result < 10

    def test_multiple_of_constraint(self, generator):
        """Test generation of numbers with multipleOf constraint."""
        test_cases = [
            # (type, multipleOf, min, max)
            ("integer", 2, 0, 100),  # Even numbers
            ("integer", 5, 0, 100),  # Multiples of 5
            ("number", 0.5, 0, 10),  # Half steps
            ("number", 0.25, 0, 10)  # Quarter steps
        ]

        for num_type, multiple, minimum, maximum in test_cases:
            schema = Schema(
                type=num_type,
                multipleOf=multiple,
                minimum=minimum,
                maximum=maximum
            )
            result = generator.generate(schema)

            # Use Decimal for precise division check
            assert Decimal(str(result)) % Decimal(str(multiple)) == 0
            assert minimum <= result <= maximum

    def test_consistent_generation(self, generator):
        """Test consistency of generated numbers with same seed."""
        schema = Schema(type="number", minimum=0, maximum=1)

        # Same schema should generate same result with same seed
        result1 = generator.generate(schema)
        result2 = generator.generate(schema)
        assert result1 == result2

        # Different seeds should generate different results
        generator2 = NumberGenerator(seed=67890)
        result3 = generator2.generate(schema)
        assert result1 != result3

    @pytest.mark.parametrize("invalid_schema,expected_error", [
        (
                Schema(type="integer", minimum=10, maximum=5),
                ERR_INVALID_BOUNDS
        ),
        (
                Schema(type="number", multipleOf=0),
                ERR_INVALID_MULTIPLE
        ),
        (
                Schema(type="number", multipleOf=-1),
                ERR_INVALID_MULTIPLE
        ),
        (
                Schema(type="number", format="invalid_format"),
                ERR_INVALID_FORMAT
        )
    ])
    def test_invalid_constraints(self, generator, invalid_schema: Schema,
                                 expected_error: str):
        """Test handling of invalid numeric constraints."""
        with pytest.raises(GeneratorError, match=expected_error):
            generator.generate(invalid_schema)

    def test_precision_handling(self, generator):
        """Test handling of floating point precision."""
        schema = Schema(
            type="number",
            multipleOf=0.1,
            minimum=0,
            maximum=1
        )
        result = generator.generate(schema)

        # Should have at most 1 decimal place
        decimal_places = len(str(result).split('.')[-1])
        assert decimal_places <= 1

        # Test with smaller precision
        precise_schema = Schema(
            type="number",
            multipleOf=0.001,
            minimum=0,
            maximum=1
        )
        precise_result = generator.generate(precise_schema)

        # Should have at most 3 decimal places
        precise_decimal_places = len(str(precise_result).split('.')[-1])
        assert precise_decimal_places <= 3
