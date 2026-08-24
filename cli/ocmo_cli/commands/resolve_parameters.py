"""ocmo resolve parameters — effective parameter values for a config."""

from __future__ import annotations

from typing import Any

import click

from .._address import parse_address_or_exit
from .._client import OcmoCtx
from .._errors import sdk_command
from .._options import namespace_option, output_option
from .._output_manifest import emit_command_output
from .._resolve_parameters_output import filter_parameters_data

_COMMAND_KEY = "resolve parameters"

_PARAMETER_TYPE_CHOICES = ("projected", "dynamic", "secret")

_PARAMETERS_HELP = """\
Show effective parameter values for a config (debug).

\b
Examples:
  ocmo -n prod resolve parameters app/web
  ocmo -n prod resolve parameters app/web@stable -o yaml
  ocmo -n prod resolve parameters app/web --type secret
  ocmo -n prod resolve parameters app/web --type projected --type dynamic
"""


@click.command("parameters", help=_PARAMETERS_HELP)
@click.argument("address")
@namespace_option()
@output_option(_COMMAND_KEY)
@click.option("--version", "-V", "version_flag", default=None, help="Version / tag to resolve.")
@click.option(
    "--type",
    "param_types",
    multiple=True,
    type=click.Choice(_PARAMETER_TYPE_CHOICES, case_sensitive=False),
    help="Filter parameters by type (repeatable).",
)
@click.pass_obj
@sdk_command
def resolve_parameters_cmd(
    ctx: OcmoCtx,
    address: str,
    namespace: str | None,
    output_fmt: str | None,
    version_flag: str | None,
    param_types: tuple[str, ...],
) -> None:
    path, version = parse_address_or_exit(address, version_flag=version_flag)

    view = ctx.namespace_view(namespace)

    kwargs: dict[str, Any] = {}
    if version:
        kwargs["version"] = version

    result = view.resolve_parameters(path, **kwargs)
    data = filter_parameters_data(result, param_types)

    emit_command_output(_COMMAND_KEY, data, output_fmt, ctx_fmt=ctx.output)
