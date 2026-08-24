"""Shared Click options for ``ocmo resolve`` and ``ocmo resolve draft``."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import click

from ._options import resolve_output_option
from ._typing import ClickDecorator

_HOOK_TIMEOUT_DEFAULT = 60


def resolve_options(
    *,
    include_version: bool = True,
    file_required: bool = False,
    output_command_key: str = "resolve",
) -> ClickDecorator:
    """Click decorator factory for shared resolve flags."""

    def decorator(cmd: Callable[..., Any]) -> Callable[..., Any]:
        return add_resolve_options(
            cmd,
            include_version=include_version,
            file_required=file_required,
            output_command_key=output_command_key,
        )

    return decorator


def add_resolve_options(
    cmd: Callable[..., Any],
    *,
    include_version: bool = True,
    file_required: bool = False,
    output_command_key: str = "resolve",
) -> Callable[..., Any]:
    """Attach resolve output, cast, filesystem, hook, and optional draft-file flags."""
    cmd = click.option(
        "--print-hooks",
        "print_hooks",
        is_flag=True,
        default=False,
        help="Print effective hook commands and exit without resolving.",
    )(cmd)
    cmd = click.option(
        "--trust-hooks",
        "trust_hooks_sha",
        default=None,
        metavar="SHA256",
        help="Trust a specific hook configuration SHA-256 (for unattended pipelines).",
    )(cmd)
    cmd = click.option(
        "--hook-timeout",
        default=_HOOK_TIMEOUT_DEFAULT,
        show_default=True,
        help="Hook execution timeout in seconds.",
    )(cmd)
    cmd = click.option(
        "--exec-hooks",
        "exec_hooks",
        is_flag=True,
        default=False,
        help="Execute resolver hooks (default: off; see OCMO_EXEC_HOOKS).",
    )(cmd)
    if include_version:
        cmd = click.option(
            "--version",
            "-V",
            "version_flag",
            default=None,
            help="Version / tag to resolve.",
        )(cmd)
    cmd = click.option(
        "--property",
        "prop_path",
        default=None,
        metavar="PATH",
        help=("Extract a json/yaml property (dot notation); with -O/--output-dir " "writes only that value."),
    )(cmd)
    cmd = click.option(
        "--trace-only",
        "trace_only",
        is_flag=True,
        default=False,
        help="Print resolve trace metadata only; perform no artifact downloads.",
    )(cmd)
    cmd = click.option(
        "--skip-existing",
        is_flag=True,
        default=False,
        help="Skip existing files that differ instead of failing.",
    )(cmd)
    cmd = click.option(
        "--rewrite",
        is_flag=True,
        default=False,
        help="Overwrite existing files that differ from the resolved content.",
    )(cmd)
    cmd = click.option(
        "--output-dir",
        default=None,
        metavar="DIR",
        help="Write each item to DIR/<item.name>. Required for folder resolve.",
    )(cmd)
    cmd = click.option(
        "-O",
        "--output-file",
        "output_file",
        default=None,
        metavar="FILE",
        help="Write single resolved item to FILE.",
    )(cmd)
    cmd = click.option(
        "--cast-option",
        "cast_options",
        multiple=True,
        metavar="KEY=VALUE",
        help="Cast options. May be repeated.",
    )(cmd)
    cmd = click.option(
        "--param",
        "params",
        multiple=True,
        metavar="KEY=VALUE",
        help="Dynamic resolve parameters. May be repeated.",
    )(cmd)
    cmd = click.option("--cast", default=None, help="Cast format (json, yaml, raw, …).")(cmd)
    cmd = resolve_output_option(output_command_key)(cmd)
    if file_required:
        cmd = click.option(
            "-f",
            "--file",
            "file_path",
            required=True,
            metavar="FILE|-",
            help="Draft config YAML from file ('-' for stdin).",
        )(cmd)
    return cmd
