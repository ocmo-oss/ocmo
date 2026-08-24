"""Tests for API error response helpers."""

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from pydantic import ValidationError as PydanticValidationError

from core.api.errors import format_django_validation_error
from core.validation_errors import (
    format_ninja_validation_errors,
    format_pydantic_validation_error,
    format_pydantic_validation_error_with_prefix,
    format_validation_error_item,
    is_response_validation_error,
)


class TestFormatDjangoValidationError(SimpleTestCase):
    def test_includes_field_names(self) -> None:
        exc = ValidationError({"description": ["This field cannot be blank."]})
        assert format_django_validation_error(exc) == [
            "description: This field cannot be blank.",
        ]


class TestFormatPydanticValidationErrors(SimpleTestCase):
    def test_body_field_missing(self) -> None:
        formatted = format_validation_error_item(
            {
                "type": "missing",
                "loc": ("body", "name"),
                "msg": "Field required",
            }
        )
        assert formatted == "name: Field required"

    def test_query_parameter_type_error(self) -> None:
        formatted = format_validation_error_item(
            {
                "type": "int_parsing",
                "loc": ("query", "limit"),
                "msg": "Input should be a valid integer, unable to parse string as an integer",
            }
        )
        assert formatted == ("query.limit: Input should be a valid integer, unable to parse string as an integer")

    def test_nested_list_index(self) -> None:
        formatted = format_validation_error_item(
            {
                "type": "missing",
                "loc": ("body", "operations", 0),
                "msg": "Field required",
            }
        )
        assert formatted == "operations[0]: Field required"

    def test_value_error_strips_prefix(self) -> None:
        formatted = format_validation_error_item(
            {
                "type": "value_error",
                "loc": ("body",),
                "msg": "Value error, At least one field must be provided",
            }
        )
        assert formatted == "At least one field must be provided"

    def test_ctx_error_is_used(self) -> None:
        formatted = format_validation_error_item(
            {
                "type": "value_error",
                "loc": ("body", "target_path"),
                "msg": "Value error, Path can't be empty",
                "ctx": {"error": "Path can't be empty"},
            }
        )
        assert formatted == "target_path: Path can't be empty"

    def test_format_ninja_validation_errors(self) -> None:
        formatted = format_ninja_validation_errors(
            [
                {
                    "type": "missing",
                    "loc": ("body", "name"),
                    "msg": "Field required",
                },
                {
                    "type": "string_pattern_mismatch",
                    "loc": ("body", "name"),
                    "msg": "String should match pattern '^[a-zA-Z0-9_-]+$'",
                },
            ]
        )
        assert formatted == [
            "name: Field required",
            "name: String should match pattern '^[a-zA-Z0-9_-]+$'",
        ]

    def test_format_pydantic_validation_error(self) -> None:
        try:
            from pydantic import BaseModel, Field

            class Sample(BaseModel):
                name: str = Field(min_length=1)

            Sample.model_validate({"name": ""})
        except PydanticValidationError as exc:
            formatted = format_pydantic_validation_error(exc)
        else:
            raise AssertionError("expected validation error")

        assert formatted == ["name: String should have at least 1 character"]

    def test_format_pydantic_validation_error_with_prefix(self) -> None:
        exc = PydanticValidationError.from_exception_data(
            "ConfigOcmoMetadataSchema",
            [
                {
                    "type": "bool_parsing",
                    "loc": ("is_json_schema",),
                    "msg": "Input should be a valid boolean, unable to interpret input",
                    "input": "blabla",
                }
            ],
        )
        assert format_pydantic_validation_error_with_prefix(exc, prefix="_ocmo") == [
            "_ocmo.is_json_schema: Input should be a valid boolean, unable to interpret input",
        ]

    def test_response_validation_detection(self) -> None:
        try:
            from pydantic import BaseModel

            class Wrapper(BaseModel):
                response: dict[str, str]

            Wrapper.model_validate({"response": {}})
        except PydanticValidationError as exc:
            assert is_response_validation_error(exc) is False

        assert is_response_validation_error(
            PydanticValidationError.from_exception_data(
                "Wrapper",
                [
                    {
                        "type": "missing",
                        "loc": ("response", "name"),
                        "msg": "Field required",
                        "input": {},
                    }
                ],
            )
        )
