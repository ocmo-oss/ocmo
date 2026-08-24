"""Root CLI entry point.

All heavy imports (SDK, yaml, httpx) are deferred into command functions so
that `ocmo --help` returns within the 200 ms budget on a warm cache.
"""

from __future__ import annotations

import os
from typing import Any

import click

from ._click_groups import LazyGroup
from ._client import OcmoCtx
from ._command_registry import HAND_WRITTEN_SHORT_HELP
from ._lazy_mixin import ClickLazyMixin
from ._output import _OUTPUT_FORMATS


def _validate_output_global(ctx: click.Context, param: click.Parameter, value: str | None) -> str | None:
    if value is None:
        return value
    if value in _OUTPUT_FORMATS or value.startswith("jsonpath="):
        return value
    valid = ", ".join(_OUTPUT_FORMATS)
    raise click.BadParameter(
        f"{value!r} is not a valid format. Valid values: {valid}, or jsonpath=<expr>.",
        ctx=ctx,
        param=param,
    )


# ---------------------------------------------------------------------------
# Global flags — attached to every invocation via callback
# ---------------------------------------------------------------------------

CONTEXT_SETTINGS = dict(help_option_names=["--help", "-h"], max_content_width=120)


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.version_option(package_name="ocmo-cli", prog_name="ocmo")
@click.option(
    "-n",
    "--namespace",
    envvar="OCMO_NAMESPACE",
    default=None,
    metavar="NS",
    help="Namespace (overrides config and OCMO_NAMESPACE).",
)
@click.option(
    "-o",
    "--output",
    "output_fmt",
    default=None,
    metavar="FORMAT",
    callback=lambda ctx, p, v: _validate_output_global(ctx, p, v),
    is_eager=False,
    help=(
        "Output format: table, json, yaml, name, path, raw, or jsonpath=<expr>. "
        "Default: table on TTY, yaml otherwise."
    ),
)
@click.option(
    "--dry-run", is_flag=True, default=False, help="Print what would be done without contacting mutating endpoints."
)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Raise log level.")
@click.option("-q", "--quiet", is_flag=True, default=False, help="Suppress non-error stderr output.")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompts.")
@click.option("--no-color", is_flag=True, default=False, envvar="OCMO_NO_COLOR", help="Disable ANSI colour.")
@click.option(
    "--skip-version-check",
    is_flag=True,
    default=False,
    envvar="OCMO_SKIP_VERSION_CHECK",
    help="Skip CLI/SDK/server version compatibility check.",
)
@click.pass_context
def cli(
    ctx: click.Context,
    namespace: str | None,
    output_fmt: str | None,
    dry_run: bool,
    verbose: bool,
    quiet: bool,
    yes: bool,
    no_color: bool,
    skip_version_check: bool,
) -> None:
    """ocmo — configuration management CLI.

    \b
    Examples:
      ocmo config set server https://ocmo.example.com
      ocmo auth login
      ocmo -n prod ls
      ocmo -n prod get item app/web
      ocmo -n prod resolve app/web --cast json
      ocmo -n prod apply -f config.yaml app/web/main
    """
    if no_color:
        os.environ["OCMO_NO_COLOR"] = "1"

    ctx.ensure_object(dict)
    ctx.obj = OcmoCtx(
        namespace=namespace,
        output=output_fmt,
        dry_run=dry_run,
        verbose=verbose,
        quiet=quiet,
        yes=yes,
        skip_version_check=skip_version_check,
        no_color=no_color,
    )

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ---------------------------------------------------------------------------
# Hand-written command modules
# ---------------------------------------------------------------------------


def _lazy_cmd(
    name: str,
    module: str,
    attr: str,
    short_help: str,
    *,
    hidden: bool = False,
) -> click.Command:
    """Return a placeholder that imports and delegates on first invocation."""

    class LazyCommand(ClickLazyMixin, click.Command):
        """A stub that replaces itself with the real command on first use."""

        def __init__(self) -> None:
            super().__init__(name)
            self.short_help = short_help
            self.hidden = hidden

        def _lazy_target(self) -> click.Command:
            return self._real()

        def _real(self) -> click.Command:
            import importlib

            mod = importlib.import_module(f".commands.{module}", package="ocmo_cli")
            cmd = getattr(mod, attr)
            assert isinstance(cmd, click.Command)
            return cmd

        def get_params(self, ctx: click.Context) -> list[click.Parameter]:
            return self._real().get_params(ctx)

        def get_help(self, ctx: click.Context) -> str:
            return self._real().get_help(ctx)

        def get_short_help_str(self, limit: int = 150) -> str:
            text = self.short_help or ""
            if limit and len(text) > limit:
                return text[: limit - 3] + "..."
            return text

        def main(  # type: ignore[override]
            self,
            args: list[str] | None = None,
            prog_name: str | None = None,
            complete_var: str | None = None,
            standalone_mode: bool = True,
            **extra: Any,
        ) -> Any:
            return self._real().main(
                args,
                prog_name=prog_name,
                complete_var=complete_var,
                standalone_mode=standalone_mode,
                **extra,
            )

    return LazyCommand()


def _register_hand_written() -> None:
    # Register lazy stubs — actual imports happen only when the command runs.
    for cli_name, (module, attr, short_help) in HAND_WRITTEN_SHORT_HELP.items():
        cli.add_command(_lazy_cmd(cli_name, module, attr, short_help), name=cli_name)


# ---------------------------------------------------------------------------
# Generated command groups (built from commands.yaml on first use)
# ---------------------------------------------------------------------------


def _build_generated_action(action: str) -> click.Group:
    from .commands.generated import build_action_group

    return build_action_group(action)


def _register_generated() -> None:
    from ._generated_registry import action_help, generated_action_names

    # Hand-written commands take precedence — skip generated groups that share a name
    existing_names = set(cli.commands or {})
    for action in generated_action_names():
        if action not in existing_names:

            def _build(action_name: str = action) -> click.Group:
                return _build_generated_action(action_name)

            cli.add_command(
                LazyGroup(
                    action,
                    help=action_help(action),
                    build_fn=_build,
                ),
                name=action,
            )

    cli.add_command(
        _lazy_cmd(
            "api",
            "api",
            "api_cmd",
            "Invoke any API operation directly by operation_id.",
            hidden=True,
        ),
        name="api",
    )

    from .commands.gp_move import register_gp_move_command
    from .commands.item_relocate import register_item_relocate_commands

    register_item_relocate_commands(cli)
    register_gp_move_command(cli)


_register_hand_written()
_register_generated()
