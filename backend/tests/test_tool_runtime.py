import pytest

from app.tools.exceptions import ToolValidationError
from app.tools.schema import validate_object_schema


def test_schema_requires_required_arguments():
    with pytest.raises(ToolValidationError):
        validate_object_schema(
            {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
            {},
        )


def test_schema_rejects_unknown_arguments():
    with pytest.raises(ToolValidationError):
        validate_object_schema(
            {"type": "object", "properties": {"url": {"type": "string"}}, "additionalProperties": False},
            {"url": "https://example.com", "secret": "bad"},
        )


def test_schema_validates_types():
    validate_object_schema(
        {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
        {"url": "https://example.com"},
    )
