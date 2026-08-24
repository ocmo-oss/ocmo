"""OCMO API request body parser (JSON APIs + raw document uploads)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ninja import NinjaAPI

from django.conf import settings
from django.http import HttpRequest
from ninja.errors import HttpError
from ninja.params.models import BodyModel
from ninja.parser import Parser
from ninja.types import DictStrAny

_JSON_CONTENT_TYPES = frozenset(
    {
        "application/json",
    }
)

_SUPPORTED_CONTENT_TYPES = frozenset(
    {
        # YAML text document
        "application/yaml",
        # JSON text document
        "application/json",
        # Plain text document
        "text/plain",
        # Jinja template text
        "text/x-jinja2",
        # Any document raw data
        "application/octet-stream",
    }
)


def normalize_content_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


class OcmoParser(Parser):
    def parse_body(self, request: HttpRequest) -> Any:
        content_type = normalize_content_type(request.content_type or "")
        if content_type == "multipart/form-data":
            raise ValueError(
                "multipart/form-data is not supported; send the document as a raw body "
                "(e.g. application/octet-stream for file bytes, or application/yaml / text/plain for text)"
            )
        elif content_type in _JSON_CONTENT_TYPES:
            # By default, Ninja parses JSON bodies as dicts to be able to retrieve specific fields.
            # We preserve this behavior for JSON routes.
            # But it means RootModel schemas should also support dict as input so that they can be validated.
            if not request.body:
                return {}
            try:
                return super().parse_body(request)
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON body") from exc
        elif content_type in _SUPPORTED_CONTENT_TYPES:
            if not request.body:
                return ""
            try:
                return request.body.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("Request body must be valid UTF-8") from exc
        else:
            raise ValueError(f"Unsupported Content-Type '{content_type}' for this endpoint")


def patch_body_model_parse_errors() -> None:
    """
    Replace Ninja's BodyModel body parsing so OcmoParser errors reach clients correctly.

    Django-Ninja reads the request body in BodyModel.get_request_data(), which calls
    api.parser.parse_body() inside a broad ``except Exception``. Any failure there becomes
    HTTP 400 with a generic ``{"detail": "Cannot parse request body"}`` message.

    OcmoParser raises ValueError for predictable client mistakes
    (unsupported Content-Type, multipart, invalid JSON on JSON routes, etc.). Without
    this patch those would all look like anonymous 400 parse failures instead of 422
    responses with the specific error text from our ValueError handlers.

    After patching:
    - ValueError from parse_body -> HttpError(422, message) for API clients
    - any other unexpected exception -> HttpError(400, ...) as before (with detail in DEBUG)

    Called once at import time so it applies before the API serves traffic.
    """

    def get_request_data(
        cls,
        request: HttpRequest,
        api: NinjaAPI,
        path_params: DictStrAny,
    ) -> DictStrAny | None:
        if request.body:
            try:
                data = api.parser.parse_body(request)
            except ValueError as exc:
                raise HttpError(422, str(exc)) from exc
            except Exception as exc:
                msg = "Cannot parse request body"
                if settings.DEBUG:
                    msg += f" ({exc})"
                raise HttpError(400, msg) from exc

            varname = getattr(cls, "__read_from_single_attr__", None)
            if varname:
                data = {varname: data}
            return data

        return None

    BodyModel.get_request_data = classmethod(get_request_data)  # type: ignore[method-assign, assignment]


patch_body_model_parse_errors()
