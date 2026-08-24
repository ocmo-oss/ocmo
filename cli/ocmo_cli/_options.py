"""Shared click option factories — keep flags consistent across all commands."""

from __future__ import annotations

import click

from ._output_manifest import manifest_output_option
from ._typing import ClickDecorator


def output_option(command_key: str) -> ClickDecorator:
    """Standard -o / --output flag with manifest-driven choices."""
    return manifest_output_option(command_key)


def get_item_output_option() -> ClickDecorator:
    """``-o`` for ``get item`` (single-item document + namespace list modes)."""
    from ._output_manifest import manifest_output_option_for_keys

    return manifest_output_option_for_keys("get item", "get item list")


def get_cast_output_option() -> ClickDecorator:
    """``-o`` for ``get cast`` (format list + per-format schema show modes)."""
    from ._output_manifest import manifest_output_option_for_keys

    return manifest_output_option_for_keys("get cast", "get cast list")


def ls_output_option() -> ClickDecorator:
    return manifest_output_option("ls")


def can_i_output_option() -> ClickDecorator:
    return manifest_output_option("can-i")


def resolve_output_option(command_key: str = "resolve") -> ClickDecorator:
    return manifest_output_option(command_key)


def tree_version_option() -> ClickDecorator:
    """Version/tag selector for tree item addresses."""
    return click.option(
        "--version",
        "-V",
        "version_flag",
        default=None,
        metavar="VER",
        help=(
            "Version or tag (latest, stable, <n>, or custom tag). " "May also be appended to the address as path@VER."
        ),
    )


def namespace_option() -> ClickDecorator:
    return click.option(
        "-n",
        "--namespace",
        default=None,
        metavar="NS",
        help="Namespace (overrides context and OCMO_NAMESPACE).",
    )


def yes_option(*, help: str = "Skip confirmation prompts.") -> ClickDecorator:
    return click.option(
        "--yes",
        "-y",
        is_flag=True,
        default=False,
        help=help,
    )


def dry_run_option(*, help: str = "Print plan without sending.") -> ClickDecorator:
    return click.option("--dry-run", is_flag=True, default=False, help=help)
