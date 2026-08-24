"""ocmo version — print CLI, SDK, and server versions with a compatibility verdict."""

from __future__ import annotations

import sys

import click

from .. import __version__ as CLI_VERSION
from .._client import OcmoCtx
from .._errors import sdk_command
from .._exit import FAILURE
from .._output import as_dict


@click.command("version")
@click.option(
    "--skip-server", is_flag=True, default=False, help="Print CLI and SDK versions only; do not contact the server."
)
@click.option("--notice", is_flag=True, default=False, help="Print the bundled product NOTICE text.")
@click.pass_obj
@sdk_command
def version_cmd(ctx: OcmoCtx, skip_server: bool, notice: bool) -> None:
    """Print CLI, SDK, and server versions with a compatibility verdict."""
    try:
        import ocmo as _sdk

        sdk_version = _sdk.__version__
    except Exception:
        sdk_version = "unknown"

    if notice:
        try:
            from .._notice import load_notice_text

            notice_text = load_notice_text()
        except Exception as exc:
            click.echo(f"Failed to load NOTICE: {exc}", err=True)
            sys.exit(FAILURE)
        print(notice_text, end="" if notice_text.endswith("\n") else "\n")
        return

    if skip_server:
        _print_versions(CLI_VERSION, sdk_version, server_version="(skipped)", verdict="")
        return

    server_version = "(unavailable)"
    verdict = ""
    try:
        info = ctx.client().version()  # type: ignore[no-untyped-call]
        data = as_dict(info)
        server_version = data.get("version", "(unknown)")
        verdict = _compatibility_verdict(sdk_version, server_version)
    except SystemExit:
        raise
    except Exception as exc:
        err_str = str(exc)
        if "OCMO_SERVER" in err_str or "required" in err_str.lower():
            server_version = "(server not configured)"
        else:
            server_version = f"(error: {exc})"
        verdict = ""

    _print_versions(CLI_VERSION, sdk_version, server_version, verdict)

    if "MAJOR MISMATCH" in verdict:
        sys.exit(FAILURE)


def _print_versions(cli: str, sdk: str, server_version: str, verdict: str) -> None:
    print(f"ocmo CLI:  {cli}")
    print(f"ocmo SDK:  {sdk}")
    print(f"Server:    {server_version}")
    if verdict:
        print(f"Compat:    {verdict}")


def _compatibility_verdict(sdk_version: str, server_version: str) -> str:
    sdk_parts = _parse_semver(sdk_version)
    srv_parts = _parse_semver(server_version)
    if not sdk_parts or not srv_parts:
        return "WARNING: could not parse one or both versions"
    sdk_major, sdk_minor, _ = sdk_parts
    srv_major, srv_minor, _ = srv_parts
    if sdk_major != srv_major:
        return f"MAJOR MISMATCH — SDK major {sdk_major} != server major {srv_major} (not compatible)"
    diff = abs(sdk_minor - srv_minor)
    if diff > 2:
        return (
            f"WARNING: minor version gap {diff} exceeds the ±2 compatibility window "
            f"(SDK {sdk_version}, server {server_version})"
        )
    return "OK"


def _parse_semver(v: str) -> tuple[int, int, int] | None:
    import re

    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", v)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))
