"""ocmo schema — render JSON Schemas for OCMO metadata and resource configuration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import click

from .._client import OcmoCtx
from .._errors import sdk_command
from .._options import namespace_option, output_option
from .._output import as_dict
from .._output_manifest import emit_command_output

_VALID_RESOURCES = "ocmo, config, resolver"


@dataclass(frozen=True)
class _SchemaSpec:
    aliases: tuple[str, ...]
    requires_address: bool
    forbids_address: bool
    usage_error: str
    fetch: Callable[[OcmoCtx, str | None, str | None], Any]


def _fetch_ocmo_schema(ctx: OcmoCtx, _namespace: str | None, _address: str | None) -> Any:
    return ctx.client().get_config_metadata_schema()  # type: ignore[no-untyped-call]


def _fetch_resolver_schema(ctx: OcmoCtx, _namespace: str | None, _address: str | None) -> Any:
    return ctx.client().get_resolver_configuration_schema()  # type: ignore[no-untyped-call]


def _fetch_config_schema(ctx: OcmoCtx, namespace: str | None, address: str | None) -> Any:
    if not address:
        raise click.UsageError(
            "ADDRESS is required for RESOURCE 'config'. " "Use: ocmo -n <namespace> schema config <path>"
        )
    return ctx.namespace_view(namespace).get_config_data_schema(path=address)


_SCHEMA_DISPATCH: dict[str, _SchemaSpec] = {
    "ocmo": _SchemaSpec(
        aliases=("ocmo",),
        requires_address=False,
        forbids_address=True,
        usage_error="ADDRESS is not used with RESOURCE 'ocmo'. Use: ocmo schema ocmo",
        fetch=_fetch_ocmo_schema,
    ),
    "config": _SchemaSpec(
        aliases=("config", "cfg", "configs"),
        requires_address=True,
        forbids_address=False,
        usage_error="",
        fetch=_fetch_config_schema,
    ),
    "resolver": _SchemaSpec(
        aliases=("resolver", "rsv", "resolvers"),
        requires_address=False,
        forbids_address=True,
        usage_error="ADDRESS is not used with RESOURCE 'resolver'. Use: ocmo schema resolver",
        fetch=_fetch_resolver_schema,
    ),
}

_SCHEMA_LOOKUP: dict[str, _SchemaSpec] = {alias: spec for spec in _SCHEMA_DISPATCH.values() for alias in spec.aliases}


@click.command("schema", help="Render the JSON Schema for a resource type.")
@click.argument("resource_type", metavar="RESOURCE", required=False)
@click.argument("address", required=False)
@namespace_option()
@output_option("schema")
@click.pass_obj
@sdk_command
def schema_cmd(
    ctx: OcmoCtx,
    resource_type: str | None,
    address: str | None,
    namespace: str | None,
    output_fmt: str | None,
) -> None:
    """Render the JSON Schema for a resource type.

    \b
    Resource types:
      ocmo               — ``_ocmo`` metadata block schema
      config / cfg       — config data schema (requires ADDRESS and -n)
      resolver / rsv     — resolver configuration schema

    \b
    Examples:
      ocmo schema ocmo                      # _ocmo block schema
      ocmo -n prod schema config app/web      # data schema for a specific config
      ocmo schema resolver                  # resolver configuration schema
    """
    if not resource_type:
        raise click.UsageError(f"RESOURCE type is required. Valid types: {_VALID_RESOURCES}")

    spec = _SCHEMA_LOOKUP.get(resource_type.lower())
    if spec is None:
        raise click.UsageError(f"Unknown resource type {resource_type!r}. Valid: {_VALID_RESOURCES}")

    if spec.forbids_address and address:
        raise click.UsageError(spec.usage_error)

    schema = spec.fetch(ctx, namespace, address)
    data = as_dict(schema)
    emit_command_output("schema", data, output_fmt, ctx_fmt=ctx.output)
