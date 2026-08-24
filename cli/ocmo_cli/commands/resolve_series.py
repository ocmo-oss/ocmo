"""ocmo resolve-series audit — time-bucketed resolve statistics."""

from __future__ import annotations

import click

from .._audit_item import resolve_audit_item
from .._client import OcmoCtx
from .._errors import sdk_command
from .._exit import USAGE_ERROR
from .._options import namespace_option, output_option
from .._output import emit, err
from .._output_manifest import emit_command_output, get_command_spec, resolve_effective_format
from .._resolve_series import resolve_bucket_seconds, resolve_time_range, series_to_dict
from .._resolve_series_chart import print_resolve_series_chart

_COMMAND_KEY = "resolve-series audit"

_AUDIT_HELP = """\
Show time-bucketed direct, nested, and error resolve counts for a tree item.

\b
Examples:
  ocmo -n prod resolve-series audit app/web
  ocmo -n prod resolve-series audit app/web -o json
  ocmo -n prod resolve-series audit app/web --from 2026-07-01T00:00:00Z
"""


@click.group("resolve-series", help="Resolve statistics over time.")
def resolve_series_group() -> None:
    """Resolve-series commands."""


@resolve_series_group.command("audit", help=_AUDIT_HELP)
@click.argument("address")
@click.option(
    "--from",
    "from_value",
    default=None,
    metavar="ISO",
    help="Range start (ISO-8601 UTC). Default: 30 days before --to.",
)
@click.option(
    "--to",
    "to_value",
    default=None,
    metavar="ISO",
    help="Range end (ISO-8601 UTC). Default: now.",
)
@click.option(
    "--bucket-seconds",
    type=int,
    default=None,
    help="Bucket size in seconds (minimum 1800). Default: auto from range.",
)
@namespace_option()
@output_option(_COMMAND_KEY)
@click.pass_obj
@sdk_command
def resolve_series_audit_cmd(
    ctx: OcmoCtx,
    address: str,
    from_value: str | None,
    to_value: str | None,
    bucket_seconds: int | None,
    namespace: str | None,
    output_fmt: str | None,
) -> None:
    view, path, node_type = resolve_audit_item(
        ctx,
        address,
        namespace,
        command="resolve-series audit",
    )

    try:
        start, end = resolve_time_range(from_value, to_value)
        bucket = resolve_bucket_seconds(start, end, override=bucket_seconds)
    except ValueError as exc:
        err(str(exc))
        raise SystemExit(USAGE_ERROR) from exc

    result = view.namespace_audit_resolve_series(
        object_id=path,
        object_type=node_type,
        from_=start,
        to=end,
        bucket_seconds=bucket,
    )
    data = series_to_dict(result)

    spec = get_command_spec(_COMMAND_KEY)
    effective_fmt = resolve_effective_format(output_fmt, ctx.output, spec)

    if effective_fmt == "chart":
        print_resolve_series_chart(
            data,
            node_type=node_type,
            range_start=start,
            range_end=end,
        )
        return

    if effective_fmt in ("json", "yaml"):
        emit(data, effective_fmt)
        return

    emit_command_output(_COMMAND_KEY, data, output_fmt, ctx_fmt=ctx.output)
