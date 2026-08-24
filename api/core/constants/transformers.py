"""Allowed parameter transformer names (validation only; runtime registry in resolve_parameters)."""

from typing import Literal, get_args

ParameterTransformer = Literal[
    "lower",
    "upper",
    "slug",
    "snake",
    "trim",
    "escape_html",
    "b64_encode",
    "urlencode",
    "int",
    "float",
    "bool",
    "null",
    "multiline",
    "omit",
]

KNOWN_TRANSFORMERS = frozenset(get_args(ParameterTransformer))
