"""ocmo completion — emit shell completion scripts.

Completion works offline (no network required).
"""

from __future__ import annotations

import os

import click
from click.shell_completion import get_completion_class

_SHELLS = ("bash", "zsh", "fish")


@click.command("completion")
@click.argument("shell", type=click.Choice(list(_SHELLS)), required=False)
def completion_cmd(shell: str | None) -> None:
    """Emit a shell completion script.

    \b
    Usage:
      # bash
      source <(ocmo completion bash)

      # zsh
      source <(ocmo completion zsh)

      # fish
      ocmo completion fish | source
    """
    if not shell:
        detected = _detect_shell()
        if detected:
            shell = detected
        else:
            raise click.UsageError(f"SHELL is required. Valid options: {', '.join(_SHELLS)}")

    comp_cls = get_completion_class(shell)
    if comp_cls is None:
        raise click.UsageError(f"Unsupported shell: {shell}")

    from ocmo_cli.main import cli

    env_var = f"_{_prog_name().upper()}_COMPLETE"
    comp = comp_cls(cli, ctx_args={}, prog_name=_prog_name(), complete_var=env_var)
    click.echo(comp.source(), nl=False)


def _detect_shell() -> str | None:
    shell_path = os.environ.get("SHELL", "")
    for s in _SHELLS:
        if s in shell_path:
            return s
    return None


def _prog_name() -> str:
    return "ocmo"
