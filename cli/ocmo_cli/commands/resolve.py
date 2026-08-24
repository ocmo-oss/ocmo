"""ocmo resolve — resolve a config or folder to its final value.

Key behaviours:
- Lazy download: artifacts only fetched when about to be written/printed.
- Default output (raw): metadata on stderr, content on stdout per item.
- --trace-only performs zero artifact downloads.
- Writes are atomic per file.
- Resolver hooks are opt-in (OCMO_EXEC_HOOKS or --exec-hooks).
- --print-hooks exits without resolving (for inspection before enabling hooks).
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import click

from .._address import parse_address_or_exit
from .._click_groups import DefaultCommandGroup
from .._client import OcmoCtx
from .._errors import sdk_command
from .._exit import FAILURE, HOOK_FAILURE, USAGE_ERROR, VALIDATION_ERROR
from .._options import namespace_option
from .._output import err, warn
from .._resolve_options import resolve_options
from .._resolve_output import (
    emit_resolve_item_metadata,
    emit_resolve_results,
    emit_write_outcome,
    emit_write_outcome_jsonpath,
    emit_write_report,
    resolve_output_format,
)
from .._resolve_write import (
    ResolveWriteOutcome,
    atomic_write,
    resolve_item_dest,
    save_resolve_item,
    write_resolve_items,
)
from .._typing import ResolvedArtifact

if TYPE_CHECKING:
    from ocmo.resolve import ResolveResult

_EXEC_HOOKS_ENV = "OCMO_EXEC_HOOKS"
_HOOK_TIMEOUT_DEFAULT = 60
_CREDENTIAL_VARS = frozenset(
    {
        "OCMO_TOKEN",
        "OCMO_CLIENT_SECRET",
        "OCMO_CLIENT_SECRET_FILE",
        "OCMO_PASSWORD",
    }
)


_RESOLVE_HELP = """\
Resolve a config or folder to its final value(s).

Default output prints resolve metadata on stderr (``# name: …``) and each
artifact on stdout. Use ``-o json`` or ``-o yaml`` for the full response with
``data`` instead of download URLs.

\b
ADDRESS format: <tree-path>[@<version>]. A trailing slash marks a folder.

\b
Examples:
  ocmo -n prod resolve app/web
  ocmo -n prod resolve app/ --output-dir ./out/
  ocmo -n prod resolve app/ -o name
  ocmo -n prod resolve app/web --cast json --param replicas=5
  ocmo -n prod resolve app/web -O ./app.json
  ocmo -n prod resolve app/ --trace-only -o json
  ocmo -n prod resolve app/web --property database.host
  ocmo -n prod resolve app/web@stable
"""


@click.group("resolve", cls=DefaultCommandGroup, default_command="_default", help=_RESOLVE_HELP)
@click.pass_context
def resolve_group(ctx: click.Context) -> None:
    """Resolve configs or inspect resolve metadata."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@resolve_group.command("_default", hidden=True)
@click.argument("address")
@namespace_option()
@resolve_options()
@click.pass_obj
@sdk_command
def resolve_cmd(
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
    version_flag: str | None,
    exec_hooks: bool,
    hook_timeout: int,
    trust_hooks_sha: str | None,
    print_hooks: bool,
) -> None:
    """Resolve a config or folder to its final value.

    \b
    Examples:
      ocmo -n prod resolve app/web
      ocmo -n prod resolve app/web --cast json --param replicas=5
      ocmo -n prod resolve app/web -O ./app.json
      ocmo -n prod resolve app/ --output-dir ./out/
      ocmo -n prod resolve app/ --trace-only -o json
      ocmo -n prod resolve app/web --property database.host
    """
    path, version = parse_address_or_exit(address, version_flag=version_flag)

    ns = ctx.require_namespace(namespace)
    view = ctx.namespace_view(namespace)

    # Parse --param and --cast-option
    params_dict = _parse_kv_args(params)
    cast_options_dict = _parse_kv_args(cast_options)

    # Build resolve kwargs
    resolve_kwargs: dict[str, Any] = {}
    if cast:
        resolve_kwargs["cast"] = cast
    if version:
        resolve_kwargs["version"] = version
    if trace_only:
        resolve_kwargs["trace_only"] = True
    if params_dict:
        resolve_kwargs["params"] = params_dict
    if cast_options_dict:
        resolve_kwargs["cast_options"] = cast_options_dict

    if ctx.dry_run:
        from .._dry_run import emit_dry_run_plan, format_resolve_dry_run  # deferred

        emit_dry_run_plan(
            format_resolve_dry_run(
                path=path,
                namespace=ns,
                cast=cast,
                parameters=params_dict or None,
            )
        )
        return

    if print_hooks:
        resolve_kwargs["trace_only"] = True

    result = view.resolve(path, **resolve_kwargs)

    # --print-hooks: show hooks and exit
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


def run_resolve_pipeline(
    ctx: OcmoCtx,
    result: ResolveResult,
    *,
    path: str,
    ns: str,
    output_fmt: str | None,
    output_file: str | None,
    output_dir: str | None,
    rewrite: bool,
    skip_existing: bool,
    trace_only: bool,
    prop_path: str | None,
    exec_hooks: bool,
    hook_timeout: int,
    trust_hooks_sha: str | None,
) -> None:
    """Shared post-resolve output: trace-only, hooks, filesystem writes, or stdout."""
    hooks_mode = _resolve_hooks_mode(exec_hooks)

    items = list(cast(Iterable[ResolvedArtifact], result))  # evaluates the lazy iterator (metadata only)

    if not items:
        warn("Resolve returned no items.")
        return

    output_fmt = resolve_output_format(output_fmt, ctx.output)

    if rewrite and skip_existing:
        err("Cannot use --rewrite and --skip-existing together.")
        raise SystemExit(USAGE_ERROR)

    # --trace-only: print metadata, no downloads
    if trace_only:
        if output_fmt == "raw":
            output_fmt = "yaml"
        emit_resolve_results(items, output_fmt, no_color=ctx.no_color, include_data=False)
        return

    # --property: stdout-only when not writing to filesystem
    if prop_path and not output_dir and not output_file:
        if len(items) != 1:
            err(f"--property requires exactly one resolved item; got {len(items)}.")
            raise SystemExit(USAGE_ERROR)
        _print_property(items[0], prop_path)
        return

    # Execute hooks when requested
    if hooks_mode != "never":
        if output_file and len(items) > 1:
            err("--output-file requires exactly one resolved item.")
            raise SystemExit(USAGE_ERROR)
        _run_with_hooks(
            result,
            items,
            path,
            ns,
            output_dir,
            output_file,
            hooks_mode=hooks_mode,
            hook_timeout=hook_timeout,
            trust_hooks_sha=trust_hooks_sha,
            yes=ctx.yes,
            rewrite=rewrite,
            skip_existing=skip_existing,
            output_fmt=output_fmt,
            no_color=ctx.no_color,
            prop_path=prop_path,
        )
        return

    # Write to filesystem
    if output_dir or output_file:
        if output_file and len(items) > 1:
            err("--output-file requires exactly one resolved item.")
            raise SystemExit(USAGE_ERROR)
        _save_and_report(
            items,
            output_file=output_file,
            output_dir=output_dir,
            rewrite=rewrite,
            skip_existing=skip_existing,
            output_fmt=output_fmt,
            no_color=ctx.no_color,
            prop_path=prop_path,
        )
        return

    emit_resolve_results(items, output_fmt, no_color=ctx.no_color)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_kv_args(args: tuple[str, ...]) -> dict[str, str]:
    result: dict[str, str] = {}
    for arg in args:
        if "=" not in arg:
            err(f"Invalid key=value argument: {arg!r}")
            raise SystemExit(USAGE_ERROR)
        k, v = arg.split("=", 1)
        result[k] = v
    return result


def _resolve_hooks_mode(exec_hooks_flag: bool) -> str:
    if exec_hooks_flag:
        return "always"
    env = os.environ.get(_EXEC_HOOKS_ENV, "never").lower()
    return env if env in ("never", "prompt", "always") else "never"


def _print_hooks(result: ResolveResult) -> None:
    hooks = _extract_hooks(result)
    if hooks is None:
        err("No hooks configured.")
        return
    for field in ("validate", "validate_all", "post_resolve", "post_resolve_all"):
        val = getattr(hooks, field, None)
        if val:
            err(f"{field}: {val}")


def _get_property_value(item: ResolvedArtifact, prop_path: str) -> Any:
    from ocmo.errors import PropertyNotFoundError, UnstructuredFormatError

    try:
        return item.get(prop_path)
    except UnstructuredFormatError as e:
        err(str(e))
        raise SystemExit(VALIDATION_ERROR)
    except PropertyNotFoundError as e:
        err(str(e))
        raise SystemExit(VALIDATION_ERROR)


def _property_value_bytes(value: Any) -> bytes:
    if isinstance(value, dict | list):
        text = json.dumps(value, default=str)
    else:
        text = str(value)
    return f"{text}\n".encode()


def _item_write_bytes(item: ResolvedArtifact, prop_path: str | None) -> tuple[bytes, bool]:
    if not prop_path:
        return item.bytes, False
    return _property_value_bytes(_get_property_value(item, prop_path)), True


def _item_data_fn(prop_path: str | None) -> Callable[[ResolvedArtifact], tuple[bytes, bool]] | None:
    if not prop_path:
        return None
    return lambda item: _item_write_bytes(item, prop_path)


def _print_property(item: ResolvedArtifact, prop_path: str) -> None:
    value = _get_property_value(item, prop_path)
    if isinstance(value, dict | list):
        print(json.dumps(value, default=str))
    else:
        print(value)


def _write_report_format(output_fmt: str) -> str:
    return output_fmt if output_fmt in ("json", "yaml") else "raw"


def _is_interleaved_save_format(output_fmt: str) -> bool:
    return output_fmt in ("raw", "name") or output_fmt.startswith("jsonpath=")


def _save_and_report(
    items: list[ResolvedArtifact],
    *,
    output_file: str | None,
    output_dir: str | None,
    rewrite: bool,
    skip_existing: bool,
    output_fmt: str,
    no_color: bool,
    prop_path: str | None = None,
) -> list[ResolveWriteOutcome]:
    output_dir_value = output_dir or (None if output_file else ".")
    item_data = _item_data_fn(prop_path)

    if _is_interleaved_save_format(output_fmt):
        if output_file and len(items) != 1:
            err("--output-file requires exactly one resolved item.")
            raise SystemExit(USAGE_ERROR)
        if output_dir_value:
            Path(output_dir_value).mkdir(parents=True, exist_ok=True)

        outcomes: list[ResolveWriteOutcome] = []
        for index, item in enumerate(items):
            if output_fmt == "raw" and index > 0:
                print(file=sys.stderr)
            if output_fmt == "raw":
                emit_resolve_item_metadata(item, no_color=no_color)
            elif output_fmt == "name":
                name = getattr(item, "name", None)
                if name:
                    print(name)
            try:
                dest = resolve_item_dest(
                    item,
                    output_file=output_file,
                    output_dir=output_dir_value or ".",
                )
            except ValueError as exc:
                err(str(exc))
                raise SystemExit(USAGE_ERROR) from exc
            data, skip_checksum = _item_write_bytes(item, prop_path)
            outcome = save_resolve_item(
                item,
                dest,
                rewrite=rewrite,
                skip_existing=skip_existing,
                data=data,
                skip_checksum=skip_checksum,
            )
            outcomes.append(outcome)
            if output_fmt == "raw" or output_fmt == "name":
                emit_write_outcome(outcome, "raw", no_color=no_color)
            elif output_fmt.startswith("jsonpath="):
                emit_write_outcome_jsonpath(outcome, output_fmt[9:])

        if any(outcome.result == "failed" for outcome in outcomes):
            raise SystemExit(FAILURE)
        return outcomes

    try:
        outcomes = write_resolve_items(
            items,
            output_file=output_file,
            output_dir=output_dir_value,
            rewrite=rewrite,
            skip_existing=skip_existing,
            item_data=item_data,
        )
    except ValueError as exc:
        err(str(exc))
        raise SystemExit(USAGE_ERROR) from exc

    emit_write_report(outcomes, _write_report_format(output_fmt), no_color=no_color)

    if any(outcome.result == "failed" for outcome in outcomes):
        raise SystemExit(FAILURE)

    return outcomes


def _run_with_hooks(
    result: ResolveResult,
    items: list[ResolvedArtifact],
    path: str,
    ns: str,
    output_dir: str | None,
    output_file: str | None,
    *,
    hooks_mode: str,
    hook_timeout: int,
    trust_hooks_sha: str | None,
    yes: bool,
    rewrite: bool,
    skip_existing: bool,
    output_fmt: str,
    no_color: bool,
    prop_path: str | None = None,
) -> None:
    """Full pipeline: stage → validate → place → post_resolve, per §13."""
    hooks = _extract_hooks(result)
    if hooks is None:
        if output_dir or output_file:
            _save_and_report(
                items,
                output_file=output_file,
                output_dir=output_dir,
                rewrite=rewrite,
                skip_existing=skip_existing,
                output_fmt=output_fmt,
                no_color=no_color,
                prop_path=prop_path,
            )
        return

    hook_block_sha = _sha256_hooks(hooks)

    # Trust pinning
    if hooks_mode == "always" and trust_hooks_sha and trust_hooks_sha != hook_block_sha:
        err(
            f"Hook configuration has changed.\n"
            f"  Expected SHA-256: {trust_hooks_sha}\n"
            f"  Current SHA-256:  {hook_block_sha}\n"
            "Re-run with --trust-hooks to accept the new configuration."
        )
        raise SystemExit(HOOK_FAILURE)

    # Consent
    if hooks_mode == "prompt":
        if not sys.stdin.isatty():
            err("Hook execution requires TTY for 'prompt' mode. Use --exec-hooks or OCMO_EXEC_HOOKS=always.")
            raise SystemExit(HOOK_FAILURE)
        print("The following hooks will be executed:", file=sys.stderr)
        _print_hooks(result)
        answer = input("Execute? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            err("Hook execution declined.")
            raise SystemExit(HOOK_FAILURE)

    # Stage into temp directory
    with tempfile.TemporaryDirectory() as staging_str:
        staging = Path(staging_str)
        staged: list[Path] = []
        for item in items:
            name = getattr(item, "name", "output")
            dest = staging / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            data, _skip_checksum = _item_write_bytes(item, prop_path)
            atomic_write(dest, data)
            staged.append(dest)

        env = _scrub_env(ns=ns, path=path, items=staged)

        # Validation phase
        _run_hook_phase(
            hooks=hooks,
            phase="validate",
            staged=staged,
            env=env,
            timeout=hook_timeout,
            quiet=False,
        )

        # Place files with checksum-aware idempotency
        outcomes = _save_and_report(
            items,
            output_file=output_file,
            output_dir=output_dir,
            rewrite=rewrite,
            skip_existing=skip_existing,
            output_fmt=output_fmt,
            no_color=no_color,
            prop_path=prop_path,
        )
        placed = [outcome.path for outcome in outcomes if outcome.result != "failed"]

        # Post-resolve phase
        env_placed = _scrub_env(ns=ns, path=path, items=placed)
        _run_hook_phase(
            hooks=hooks,
            phase="post_resolve",
            staged=placed,
            env=env_placed,
            timeout=hook_timeout,
            quiet=False,
        )


def _extract_hooks(result: ResolveResult) -> Any | None:
    resolver = getattr(result, "resolver", None)
    if resolver is None:
        return None
    hooks = getattr(resolver, "hooks", None)
    if hooks is None:
        return None
    # Check if any hook is set
    for field in ("validate", "validate_all", "post_resolve", "post_resolve_all"):
        if getattr(hooks, field, None):
            return hooks
    return None


def _sha256_hooks(hooks: Any) -> str:
    parts = []
    for field in ("validate", "validate_all", "post_resolve", "post_resolve_all"):
        v = getattr(hooks, field, None) or ""
        parts.append(f"{field}={v}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _scrub_env(ns: str, path: str, items: list[Path]) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _CREDENTIAL_VARS}
    env["OCMO_HOOK_NAMESPACE"] = ns
    env["OCMO_HOOK_PATH"] = path
    env["OCMO_HOOK_ITEM"] = str(items[0]) if items else ""
    env["OCMO_HOOK_FILES"] = " ".join(shlex.quote(str(p)) for p in items)
    return env


def _run_hook_phase(
    *,
    hooks: Any,
    phase: str,
    staged: list[Path],
    env: dict[str, str],
    timeout: int,
    quiet: bool,
) -> None:
    """Run the validate or post_resolve hook phase — exactly one of per/all."""
    per_hook = getattr(hooks, phase, None)
    all_hook = getattr(hooks, f"{phase}_all", None)

    if all_hook:
        all_paths = " ".join(shlex.quote(str(p)) for p in staged)
        cmd = all_hook.replace("{!conf}", all_paths) if "{!conf}" in all_hook else f"{all_hook} {all_paths}"
        if not quiet:
            err(f"[hook:{phase}_all] {cmd}")
        _exec_hook(cmd, env=env, timeout=timeout, cwd=str(staged[0].parent) if staged else ".")
    elif per_hook:
        for item_path in staged:
            quoted = shlex.quote(str(item_path))
            cmd = per_hook.replace("{!conf}", quoted) if "{!conf}" in per_hook else f"{per_hook} {quoted}"
            if not quiet:
                err(f"[hook:{phase}] {cmd}")
            _exec_hook(cmd, env=env, timeout=timeout, cwd=str(item_path.parent))


def _exec_hook(cmd: str, *, env: dict[str, str], timeout: int, cwd: str) -> None:
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            env=env,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            out, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            err(f"Hook timed out after {timeout}s: {cmd!r}")
            raise SystemExit(HOOK_FAILURE)

        prefix = "[hook] "
        for line in out.splitlines():
            err(f"{prefix}{line}")

        if proc.returncode != 0:
            err(f"Hook failed (exit {proc.returncode}): {cmd!r}")
            raise SystemExit(HOOK_FAILURE)

    except SystemExit:
        raise
    except Exception as exc:
        err(f"Hook execution error: {exc}")
        raise SystemExit(HOOK_FAILURE)


from .resolve_parameters import resolve_parameters_cmd  # noqa: E402

resolve_group.add_command(resolve_parameters_cmd)

from .resolve_draft import resolve_draft_cmd  # noqa: E402

resolve_group.add_command(resolve_draft_cmd)
