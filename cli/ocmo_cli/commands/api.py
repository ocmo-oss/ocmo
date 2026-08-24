"""ocmo api — escape hatch to invoke any SDK operation directly.

This is the guarantee that no API capability is ever unreachable from the CLI.
Prints raw JSON. Bypasses all ergonomic layers.
"""

from __future__ import annotations

import sys
from typing import Any, NoReturn

import click

from .._client import OcmoCtx
from .._errors import handle_sdk_error
from .._output import as_dict, emit


@click.command("api", hidden=True)
@click.argument("operation_id")
@click.option(
    "--param", "-p", "params", multiple=True, metavar="KEY=VALUE", help="Operation parameters (may be repeated)."
)
@click.option(
    "-f", "--file", "file_path", default=None, metavar="FILE|-", help="Request body from file ('-' for stdin)."
)
@click.option("-n", "--namespace", default=None)
@click.pass_obj
def api_cmd(
    ctx: OcmoCtx,
    operation_id: str,
    params: tuple[str, ...],
    file_path: str | None,
    namespace: str | None,
) -> None:
    """Invoke any API operation directly by operation_id.

    This is the escape hatch for operations marked `skip` in commands.yaml,
    and for advanced usage. Output is always raw JSON.

    \b
    Examples:
      ocmo api whoami
      ocmo api get_item --param path=app/web -n prod
      ocmo api create_config --param path=app/new -f body.yaml -n prod
    """
    kwargs: dict[str, Any] = {}

    # Parse --param
    for p in params:
        if "=" not in p:
            print(f"Error: --param must be KEY=VALUE, got {p!r}", file=sys.stderr)
            raise SystemExit(2)
        k, v = p.split("=", 1)
        kwargs[k] = v

    # Read body
    if file_path:
        if file_path == "-":
            kwargs["content"] = sys.stdin.read()
        else:
            with open(file_path) as f:
                kwargs["content"] = f.read()

    try:
        result = _dispatch(ctx, operation_id, namespace, kwargs)
        if result is not None:
            if isinstance(result, list):
                emit([as_dict(item) for item in result], "json")
            else:
                payload = as_dict(result, fallback_vars=False) or result
                emit(payload, "json")
    except KeyboardInterrupt:
        raise SystemExit(130)
    except SystemExit:
        raise
    except Exception as exc:
        handle_sdk_error(exc)


def _dispatch(ctx: OcmoCtx, op_id: str, namespace: str | None, kwargs: dict[str, Any]) -> Any:
    """Find the SDK method and call it."""
    from pathlib import Path

    import yaml  # deferred

    ops_path = Path(__file__).parent.parent.parent.parent / "sdk" / "operations.yaml"
    scope = "namespace"
    if ops_path.exists():
        with ops_path.open() as f:
            ops = yaml.safe_load(f) or {}
        op_cfg = ops.get("operations", {}).get(op_id, {})
        scope = op_cfg.get("scope", "namespace")

    if scope == "client":
        client = ctx.client()
        method = getattr(client, op_id, None)
        if method is None:
            _no_such_op(op_id)
        assert method is not None
        return method(**kwargs)
    else:
        ns = namespace or ctx.namespace
        if ns:
            view = ctx.ns(ns)
        else:
            # Try client first, then ask for namespace
            client = ctx.client()
            method = getattr(client, op_id, None)
            if method:
                return method(**kwargs)
            ctx.require_namespace(namespace)  # will abort with error
            raise SystemExit(2)  # unreachable but satisfies type checker

        method = getattr(view, op_id, None)
        if method is None:
            _no_such_op(op_id)
        assert method is not None
        return method(**kwargs)


def _no_such_op(op_id: str) -> NoReturn:
    print(f"Error: unknown operation {op_id!r}.", file=sys.stderr)
    print("Run `ocmo api --help` or check the SDK documentation for valid operation IDs.", file=sys.stderr)
    raise SystemExit(2)
