# Module docstring explaining purpose of base schema module
"""Base Pydantic response schema with camelCase alias generation and dual-casing support."""

# Import re module for regular expression pattern matching and casing conversion
import re
# Import typing utilities for structured dictionary types and any values
from typing import Any, Dict
# Import Pydantic BaseModel, ConfigDict, and model_serializer decorator
from pydantic import BaseModel, ConfigDict, model_serializer
# Import to_camel alias generator from pydantic.alias_generators
from pydantic.alias_generators import to_camel


# Helper function to convert camelCase or PascalCase strings to snake_case
def to_snake_case(name: str) -> str:
    """Convert camelCase or PascalCase string to snake_case.

    Args:
        name (str): Identifier in camelCase or PascalCase.

    Returns:
        str: Converted snake_case identifier string.

    Example:
        >>> to_snake_case("studentName")
        'student_name'
    """
    # Insert underscore between lowercase/number character and uppercase character
    s = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    # Convert trailing uppercase segments and cast entirely to lowercase
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s).lower()


# Base class for all Verism API response schemas
class VerismBaseModel(BaseModel):
    """Base Pydantic schema supporting:
    - ORM attribute reading (from_attributes=True)
    - Population by attribute name or camelCase alias (populate_by_name=True)
    - Automatic camelCase alias generation (alias_generator=to_camel)
    - Serialization providing both camelCase and snake_case keys to guarantee
      complete frontend compatibility across all components.
    """

    # Model configuration dictionary configuring camelCase aliases and ORM support
    model_config = ConfigDict(
        # Allow population directly from SQLAlchemy ORM model instances
        from_attributes=True,
        # Allow initializing models by field name or alias
        populate_by_name=True,
        # Generate camelCase aliases automatically for all snake_case attributes
        alias_generator=to_camel,
        # Ignore unexpected fields gracefully
        extra="ignore",
    )

    # Wrap model serialization to ensure both camelCase and snake_case keys are emitted
    @model_serializer(mode="wrap")
    def serialize_dual_keys(self, handler) -> Dict[str, Any]:
        """Wrap serializer to ensure both camelCase and snake_case keys are present.

        Args:
            handler: Upstream serialization handler callable.

        Returns:
            Dict[str, Any]: Dictionary containing both camelCase and snake_case keys.
        """
        # Execute default Pydantic serialization
        data = handler(self)
        # If output is not a dictionary, return as-is
        if not isinstance(data, dict):
            # Return primitive or non-dict value
            return data

        # Shallow copy result dictionary to preserve original pairs
        result = dict(data)
        # Iterate over all serialized key-value pairs
        for key, value in list(data.items()):
            # Compute snake_case variant of the key
            snake_key = to_snake_case(key)
            # If snake_case key is not yet present in dictionary, assign it
            if snake_key not in result:
                # Add snake_case key mapping to value
                result[snake_key] = value
            # Compute camelCase variant of the key
            camel_key = to_camel(key)
            # If camelCase key is not yet present in dictionary, assign it
            if camel_key not in result:
                # Add camelCase key mapping to value
                result[camel_key] = value
        # Return enriched dictionary containing both key conventions
        return result
