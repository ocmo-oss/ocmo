"""ocmo resolve draft — resolve unsaved config YAML without persisting it."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .._address import parse_simple_address_or_exit, reject_version
from .._client import OcmoCtx
from .._errors import sdk_command
from .._options import namespace_option
from .._resolve_draft import call_resolve_draft
from .._resolve_options import resolve_options

_DRAFT_HELP = """\
Resolve unsaved draft YAML at ADDRESS without persisting it.

Uses the same output, cast, parameter, filesystem, and hook options as
``ocmo resolve``. Draft content is read from ``-f/--file`` (or stdin via ``-``).

\b
Examples:
  ocmo -n prod resolve draft app/web -f draft.yaml
  ocmo -n prod resolve draft app/web -f - --cast json < draft.yaml
  ocmo -n prod resolve draft app/web -f draft.yaml --trace-only -o yaml
"""


@click.command("draft", help=_DRAFT_HELP)
@click.argument("address")
@namespace_option()
@resolve_options(include_version=False, file_required=True)
@click.pass_obj
@sdk_command
def resolve_draft_cmd(
    ctx: OcmoCtx,
    address: str,
    namespace: str | None,
    output_fmt: str | None,
    cast: str | None,
    params: tuple[str, ...],
    cast_options: tuple[str, ...],
    output_file: str | None,
    output_dir: str | None,
    rewrite: bool,
    skip_existing: bool,
    trace_only: bool,
    prop_path: str | None,
    exec_hooks: bool,
    hook_timeout: int,
    trust_hooks_sha: str | None,
    print_hooks: bool,
    file_path: str,
) -> None:
    from .resolve import _parse_kv_args, _print_hooks, run_resolve_pipeline

    path, version = parse_simple_address_or_exit(address)
    reject_version(version, command="resolve draft")

    content = sys.stdin.read() if file_path == "-" else Path(file_path).read_text()

    params_dict = _parse_kv_args(params)
    cast_options_dict = _parse_kv_args(cast_options)

    view = ctx.namespace_view(namespace)
    ns = ctx.require_namespace(namespace)

    if print_hooks:
        trace_only = True

    result = call_resolve_draft(
        view,
        path,
        content=content,
        cast=cast,
        trace_only=trace_only,
        params=params_dict or None,
        cast_options=cast_options_dict or None,
    )

    if print_hooks:
        _print_hooks(result)
        return

    run_resolve_pipeline(
        ctx,
        result,
        path=path,
        ns=ns,
        output_fmt=output_fmt,
        output_file=output_file,
        output_dir=output_dir,
        rewrite=rewrite,
        skip_existing=skip_existing,
        trace_only=trace_only,
        prop_path=prop_path,
        exec_hooks=exec_hooks,
        hook_timeout=hook_timeout,
        trust_hooks_sha=trust_hooks_sha,
    )
