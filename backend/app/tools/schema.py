from typing import Any

from app.tools.exceptions import ToolValidationError


def validate_object_schema(schema: dict[str, Any], arguments: dict[str, Any]) -> None:
    if schema.get("type") != "object":
        raise ToolValidationError("INVALID_SCHEMA", "Tool schema must be an object schema")

    properties = schema.get("properties", {})
    required = schema.get("required", [])
    additional = schema.get("additionalProperties", False)

    missing = [name for name in required if name not in arguments]
    if missing:
        raise ToolValidationError("INVALID_ARGUMENTS", f"Missing required arguments: {', '.join(missing)}")

    if not additional:
        unknown = [name for name in arguments if name not in properties]
        if unknown:
            raise ToolValidationError("INVALID_ARGUMENTS", f"Unknown arguments: {', '.join(unknown)}")

    for name, value in arguments.items():
        spec = properties.get(name, {})
        expected = spec.get("type")
        valid = {
            "string": isinstance(value, str),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
            "object": isinstance(value, dict),
            "array": isinstance(value, list),
        }.get(expected, True)
        if not valid:
            raise ToolValidationError("INVALID_ARGUMENTS", f"Argument '{name}' has invalid type")
