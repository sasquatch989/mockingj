"""Schema Model Definitions.

This module contains Pydantic models for OpenAPI/Swagger schema validation.

File path: src/mockingj/models/schema.py
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union, Set, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import re

# Type aliases
Properties = Dict[str, "Schema"]
PatternProperties = Dict[str, "Schema"]
Dependencies = Dict[str, Union[List[str], "Schema"]]


class StringFormat(str, Enum):
    """Valid string formats in OpenAPI/Swagger."""
    DATE = "date"
    DATETIME = "date-time"
    PASSWORD = "password"
    BYTE = "byte"
    BINARY = "binary"
    EMAIL = "email"
    UUID = "uuid"
    URI = "uri"
    HOSTNAME = "hostname"
    IPV4 = "ipv4"
    IPV6 = "ipv6"


class NumberFormat(str, Enum):
    """Valid number formats in OpenAPI/Swagger."""
    FLOAT = "float"
    DOUBLE = "double"
    INT32 = "int32"
    INT64 = "int64"


class Schema(BaseModel):
    """Base schema model for OpenAPI/Swagger specifications."""
    type: Optional[str] = None
    format: Optional[str] = None
    description: Optional[str] = None
    default: Optional[Any] = None
    title: Optional[str] = None
    example: Optional[Any] = None
    examples: Optional[List[Any]] = None
    nullable: bool = False
    ref: Optional[str] = Field(None, alias="$ref")
    enum: Optional[List[Any]] = None
    
    # Object-specific fields
    properties: Optional[Dict[str, 'Schema']] = None
    required: Optional[List[str]] = None
    additionalProperties: Optional[Union[bool, 'Schema']] = None
    minProperties: Optional[int] = Field(None, ge=0)
    maxProperties: Optional[int] = Field(None, ge=0)
    patternProperties: Optional[Dict[str, 'Schema']] = None
    dependencies: Optional[Dict[str, Union[List[str], 'Schema']]] = None
    
    # String-specific fields
    minLength: Optional[int] = Field(None, ge=0)
    maxLength: Optional[int] = Field(None, ge=0)
    pattern: Optional[str] = None
    
    # Number-specific fields
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    exclusiveMinimum: bool = False
    exclusiveMaximum: bool = False
    multipleOf: Optional[float] = Field(None, gt=0)

    @model_validator(mode='before')
    @classmethod
    def validate_refs(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate schema references before other validation."""
        if '$ref' in values:
            # Schema with $ref should not have other fields except description
            allowed_fields = {'$ref', 'description'}
            excluded_fields = {k: v for k, v in values.items()
                             if k not in allowed_fields and v is not None}
            if excluded_fields:
                raise ValueError(
                    f"Schema with $ref cannot have additional fields: {', '.join(excluded_fields.keys())}"
                )
        return values

    @model_validator(mode='after')
    def validate_combined_type_ref(self) -> 'Schema':
        """Ensure type and ref are not used together."""
        if self.ref is not None and self.type is not None:
            raise ValueError("Cannot specify both $ref and type in schema")
        return self

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate schema type."""
        if v is not None and v not in {
            "string", "number", "integer", "boolean", "array", "object", "null"
        }:
            raise ValueError("Invalid schema type")
        return v

    @model_validator(mode='after')
    def validate_object_properties(self) -> 'Schema':
        """Validate object-specific properties."""
        if self.type == "object":
            # Validate required properties exist in properties
            if self.required and self.properties:
                missing = [prop for prop in self.required if prop not in self.properties]
                if missing:
                    raise ValueError(f"Required properties missing: {', '.join(missing)}")
            
            # Validate property dependencies
            if self.dependencies and self.properties:
                for prop, deps in self.dependencies.items():
                    if isinstance(deps, list):
                        missing = [dep for dep in deps if dep not in self.properties]
                        if missing:
                            raise ValueError(f"Dependency properties missing: {', '.join(missing)}")
            
            # Validate property counts
            if self.minProperties is not None and self.maxProperties is not None:
                if self.maxProperties < self.minProperties:
                    raise ValueError("maxProperties must be >= minProperties")
        
        return self

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: Optional[str], info: Dict[str, Any]) -> Optional[str]:
        """Validate format based on type."""
        if v is None:
            return v

        schema_type = info.data.get('type')
        if schema_type == "string":
            try:
                StringFormat(v)
                return v
            except ValueError:
                raise ValueError(f"Invalid string format: {v}")
        elif schema_type in ("number", "integer"):
            try:
                NumberFormat(v)
                return v
            except ValueError:
                raise ValueError(f"Invalid number format: {v}")
        return v

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: Optional[str]) -> Optional[str]:
        """Validate regex pattern."""
        if v is not None:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regular expression pattern: {e}")
        return v

    @field_validator("enum")
    @classmethod
    def validate_enum(cls, v: Optional[List[Any]]) -> Optional[List[Any]]:
        """Validate enum values."""
        if v is not None:
            # Check for duplicates using string representation
            seen = set()
            for item in v:
                item_str = str(item)
                if item_str in seen:
                    raise ValueError("Duplicate values in enum")
                seen.add(item_str)
        return v

    @model_validator(mode='after')
    def validate_constraints(self) -> 'Schema':
        """Validate type-specific constraints."""
        # String constraints
        if self.type == "string":
            if self.maxLength is not None and self.minLength is not None:
                if self.maxLength < self.minLength:
                    raise ValueError("maxLength must be >= minLength")
                    
        # Numeric constraints
        if self.type in ("number", "integer"):
            if self.maximum is not None and self.minimum is not None:
                if self.maximum < self.minimum:
                    raise ValueError("maximum must be >= minimum")
                    
            if self.multipleOf is not None and self.multipleOf <= 0:
                raise ValueError("multipleOf must be > 0")

        # Default value type validation
        if self.default is not None and self.type is not None:
            type_map = {
                "string": str,
                "number": (int, float),
                "integer": int,
                "boolean": bool,
                "array": list,
                "object": dict
            }
            expected_type = type_map.get(self.type)
            if expected_type:
                if not isinstance(self.default, expected_type):
                    raise ValueError(
                        f"Default value type does not match schema type: {self.type}"
                    )

                # Additional validation for numeric types
                if self.type == "integer" and isinstance(self.default, float):
                    raise ValueError("Integer schema cannot have float default value")

        return self

    model_config = ConfigDict(
        validate_assignment=True,
        populate_by_name=True,
        extra='allow'  # Allow extra fields for subclass compatibility
    )


class ArraySchema(Schema):
    """Schema model for array types."""
    type: str = "array"
    items: Union[Schema, List[Schema]]  # Single schema or tuple validation
    minItems: Optional[int] = Field(None, ge=0)
    maxItems: Optional[int] = Field(None, ge=0)
    uniqueItems: bool = False
    additionalItems: Union[bool, Schema, None] = None
    contains: Optional[Schema] = None
    minContains: Optional[int] = Field(None, ge=1)
    maxContains: Optional[int] = Field(None, ge=1)

    @field_validator('items')
    @classmethod
    def validate_items(cls, v: Union[Schema, List[Schema]]) -> Union[Schema, List[Schema]]:
        """Validate items schema."""
        if isinstance(v, list):
            if not v:
                raise ValueError("Items list cannot be empty")
            if not all(isinstance(item, Schema) for item in v):
                raise ValueError("All items must be valid schemas")
        elif not isinstance(v, Schema):
            raise ValueError("Items must be a valid schema")
        return v

    @field_validator('maxItems')
    @classmethod
    def validate_max_items(cls, v: Optional[int], info: Dict[str, Any]) -> Optional[int]:
        """Validate maxItems is greater than or equal to minItems."""
        if v is not None and info.data.get('minItems') is not None:
            if v < info.data['minItems']:
                raise ValueError("maxItems must be >= minItems")
        return v

    @field_validator('maxContains')
    @classmethod
    def validate_max_contains(cls, v: Optional[int], info: Dict[str, Any]) -> Optional[int]:
        """Validate maxContains constraints."""
        if v is not None:
            min_contains = info.data.get('minContains')
            if min_contains is not None and v < min_contains:
                raise ValueError("maxContains must be >= minContains")
        return v

    def _validate_item_type(self, item: Any, schema: Schema) -> bool:
        """Validate an item against a schema type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        expected_type = type_map.get(schema.type)
        if expected_type is None:
            return True
        if schema.type == "integer" and isinstance(item, float):
            return False
        return isinstance(item, expected_type)

    @model_validator(mode='after')
    def validate_schema(self) -> 'ArraySchema':
        """Validate array schema constraints."""
        # Length constraints
        if self.minItems is not None and self.maxItems is not None:
            if self.maxItems < self.minItems:
                raise ValueError("maxItems must be >= minItems")

        # Contains constraints
        if self.contains is not None:
            if not isinstance(self.contains, Schema):
                raise ValueError("Contains must be a valid schema")
            if self.minContains is not None and self.minContains < 1:
                raise ValueError("minContains must be >= 1")
            if self.maxContains is not None and self.minContains is not None:
                if self.maxContains < self.minContains:
                    raise ValueError("maxContains must be >= minContains")

        # Default value validation
        if self.default is not None:
            if not isinstance(self.default, list):
                raise ValueError("Default value must be an array")
            
            # Length validation
            if self.minItems is not None and len(self.default) < self.minItems:
                raise ValueError(f"Default array length {len(self.default)} is less than minItems {self.minItems}")
            if self.maxItems is not None and len(self.default) > self.maxItems:
                raise ValueError(f"Default array length {len(self.default)} is greater than maxItems {self.maxItems}")
            
            # Unique items validation
            if self.uniqueItems:
                if len(set(map(str, self.default))) != len(self.default):
                    raise ValueError("Default items must be unique when uniqueItems is true")

            # Items validation
            if isinstance(self.items, Schema):
                for item in self.default:
                    if not self._validate_item_type(item, self.items):
                        raise ValueError("Default items must match schema type")
            elif isinstance(self.items, list):
                if len(self.default) > len(self.items) and self.additionalItems is False:
                    raise ValueError("Default array contains more items than allowed by tuple validation")
                for i, item in enumerate(self.default):
                    if i < len(self.items):
                        if not self._validate_item_type(item, self.items[i]):
                            raise ValueError(f"Default item at position {i} does not match schema")

        # Examples validation
        if self.examples is not None:
            if not isinstance(self.examples, list):
                raise ValueError("Examples must be an array")
            for example in self.examples:
                if not isinstance(example, list):
                    raise ValueError("Each example must be an array")
                
                # Length validation
                if self.minItems is not None and len(example) < self.minItems:
                    raise ValueError(f"Example array length {len(example)} is less than minItems {self.minItems}")
                if self.maxItems is not None and len(example) > self.maxItems:
                    raise ValueError(f"Example array length {len(example)} is greater than maxItems {self.maxItems}")
                
                # Unique items validation
                if self.uniqueItems and len(set(map(str, example))) != len(example):
                    raise ValueError("Example items must be unique when uniqueItems is true")
                
                # Items validation
                if isinstance(self.items, Schema):
                    for item in example:
                        if not self._validate_item_type(item, self.items):
                            raise ValueError("Example items must match schema type")
                elif isinstance(self.items, list):
                    if len(example) > len(self.items) and self.additionalItems is False:
                        raise ValueError("Example contains more items than allowed by tuple validation")
                    for i, item in enumerate(example):
                        if i < len(self.items):
                            if not self._validate_item_type(item, self.items[i]):
                                raise ValueError(f"Example item at position {i} does not match schema")

        return self


class ObjectSchema(Schema):
    """Schema model for object types."""
    type: str = "object"
    properties: Properties = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)
    additionalProperties: Union[bool, Schema] = True
    minProperties: Optional[int] = Field(None, ge=0)
    maxProperties: Optional[int] = Field(None, ge=0)
    patternProperties: PatternProperties = Field(default_factory=dict)
    dependencies: Dependencies = Field(default_factory=dict)
    
    @field_validator("required")
    @classmethod
    def validate_required(cls, v: List[str], info: Dict[str, Any]) -> List[str]:
        """Validate required properties exist in properties."""
        properties = info.data.get("properties", {})
        for prop in v:
            if prop not in properties:
                raise ValueError(f"Required property not found: {prop}")
        return v

    @field_validator("patternProperties")
    @classmethod
    def validate_patterns(cls, v: PatternProperties) -> PatternProperties:
        """Validate pattern property regular expressions."""
        for pattern in v.keys():
            try:
                re.compile(pattern)
            except re.error:
                raise ValueError(f"Invalid regex pattern: {pattern}")
        return v

    @field_validator("maxProperties")
    @classmethod
    def validate_max_properties(cls, v: Optional[int], info: Dict[str, Any]) -> Optional[int]:
        """Validate maxProperties is greater than or equal to minProperties."""
        if v is not None and info.data.get("minProperties") is not None:
            if v < info.data["minProperties"]:
                raise ValueError("maxProperties must be >= minProperties")
        return v

    @model_validator(mode='after')
    def validate_schema(self) -> 'ObjectSchema':
        """Validate object schema constraints."""
        # Property counts
        if self.minProperties is not None and self.maxProperties is not None:
            if self.maxProperties < self.minProperties:
                raise ValueError("maxProperties must be >= minProperties")

        # Dependencies
        for prop, deps in self.dependencies.items():
            if isinstance(deps, list):
                for dep in deps:
                    if dep not in self.properties:
                        raise ValueError(f"Dependency {dep} not found in properties")
            elif isinstance(deps, Schema):
                # Schema dependency validation could be added here
                pass
            else:
                raise ValueError("Dependencies must be either a list of property names or a schema")

        return self


PropertySchema = Schema  #