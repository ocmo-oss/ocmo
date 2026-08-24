"""ocmo export — write a namespace subtree to disk.

One file per item at its tree path. Secrets excluded unless --reveal-secrets.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import click

from .._address import parse_address_or_exit
from .._client import OcmoCtx
from .._errors import sdk_command
from .._export_metadata import (
    export_metadata_rows,
    metadata_file_prefix,
    write_export_xattrs,
)
from .._item_output import item_body
from .._options import yes_option
from .._output import as_dict, err, warn


@click.command("export")
@click.argument("address")
@click.option("--to", "dest_dir", required=True, metavar="DIR", help="Target directory for exported files.")
@click.option("-n", "--namespace", default=None)
@click.option("--version", "-V", "version_flag", default=None, help="Version / tag to export (default: latest).")
@click.option(
    "--reveal-secrets", is_flag=True, default=False, help="Include secrets with decrypted values. Requires --yes."
)
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing files.")
@click.option(
    "--fail-on-missing", is_flag=True, default=False, help="Exit non-zero if any item lacks the requested version/tag."
)
@click.option(
    "--metadata", is_flag=True, default=False, help="Embed item metadata in exported files and xattrs (user.ocmo.*)."
)
@click.option("--dry-run", is_flag=True, default=False)
@yes_option()
@click.pass_obj
@sdk_command
def export_cmd(
    ctx: OcmoCtx,
    address: str,
    dest_dir: str,
    namespace: str | None,
    version_flag: str | None,
    reveal_secrets: bool,
    overwrite: bool,
    fail_on_missing: bool,
    metadata: bool,
    dry_run: bool,
    yes: bool,
) -> None:
    """Export a subtree to disk, preserving tree structure.

    \b
    Examples:
      ocmo -n prod export app/ --to ./backup/
      ocmo -n prod export app/ --to ./backup/ --version stable
      ocmo -n prod export app/ --to ./backup/ --reveal-secrets --yes
    """
    path, version = parse_address_or_exit(address, version_flag=version_flag)

    if reveal_secrets and not (yes or ctx.yes):
        if sys.stdin.isatty():
            warn("--reveal-secrets will export decrypted secret values to disk.")
            from .._mutating import run_mutating

            run_mutating(
                ctx,
                dry_run=False,
                yes=False,
                plan_lines=None,
                confirm_message="Continue with revealed secrets?",
                action=lambda: None,
                abort_exit_code=1,
                abort_via_err=True,
            )
        else:
            err("--reveal-secrets requires --yes in non-interactive mode.")
            raise SystemExit(1)

    ns = ctx.require_namespace(namespace)
    dest = Path(dest_dir)

    if not (dry_run or ctx.dry_run):
        _check_dest_permissions(dest, reveal_secrets)

    view = ctx.namespace_view(namespace)
    result = view.navigate_path(path=path.rstrip("/"))

    data = as_dict(result)
    children = data.get("children") or []

    items_to_export = _collect_items(children, include_secrets=reveal_secrets)

    if not items_to_export:
        warn(f"No items found under {path!r}.")
        return

    if dry_run or ctx.dry_run:
        from .._dry_run import emit_dry_run_plan, format_export_dry_run  # deferred

        base = path.rstrip("/")
        for item in items_to_export:
            item_path = item.get("path") or item.get("name", "")
            rel = _relative_export_path(item_path, base)
            dest_file = _safe_join(dest, rel)
            emit_dry_run_plan(
                format_export_dry_run(
                    item_path=item_path,
                    dest_file=str(dest_file),
                    namespace=ns,
                )
            )
        return

    skipped = failed = exported = 0
    base = path.rstrip("/")

    for item_meta in items_to_export:
        item_path = item_meta.get("path") or item_meta.get("name", "")
        node_type = item_meta.get("node_type") or item_meta.get("type", "config")
        item_version = version or "latest"

        rel = _relative_export_path(item_path, base)
        dest_file = _safe_join(dest, rel)

        if dest_file.exists() and not overwrite:
            warn(f"Skipping {rel!r}: file exists (use --overwrite).")
            skipped += 1
            continue

        try:
            get_kwargs: dict[str, Any] = {"version": item_version}
            if node_type == "secret" and reveal_secrets:
                get_kwargs["reveal"] = True

            raw_item = view.get_item(path=item_path, **get_kwargs)
            content = item_body(raw_item)
            meta_rows = export_metadata_rows(raw_item, namespace=ns) if metadata else []
            if metadata:
                content = metadata_file_prefix(meta_rows, node_type=node_type) + content

            if not content and fail_on_missing:
                err(f"Item {item_path!r} has no content at version {item_version!r}.")
                raise SystemExit(1)

            dest_file.parent.mkdir(parents=True, exist_ok=True)
            mode = 0o600 if node_type == "secret" else 0o644
            _atomic_write_text(dest_file, content, mode=mode)
            if metadata:
                write_export_xattrs(dest_file, meta_rows)

            if sys.stderr.isatty():
                err(f"Exported: {rel}")
            exported += 1

        except SystemExit:
            raise
        except Exception as exc:
            if fail_on_missing and "not found" in str(exc).lower():
                err(f"Item {item_path!r} not found at version {item_version!r}: {exc}")
                raise SystemExit(1) from exc
            warn(f"Failed to export {item_path!r}: {exc}")
            failed += 1

    print(f"Exported {exported} items, skipped {skipped}, failed {failed}.", file=sys.stderr)
    if failed:
        raise SystemExit(1)


def _relative_export_path(item_path: str, base: str) -> str:
    base = base.rstrip("/")
    if not base:
        return item_path
    if item_path == base:
        return ""
    prefix = f"{base}/"
    if item_path.startswith(prefix):
        return item_path[len(prefix) :]
    return item_path


def _collect_items(children: list[Any], *, include_secrets: bool) -> list[dict[str, Any]]:
    """Flatten tree children, optionally excluding secrets."""
    result: list[dict[str, Any]] = []
    for item in children:
        node = item if isinstance(item, dict) else vars(item)
        node_type = node.get("node_type") or node.get("type", "")
        if node_type == "folder":
            result.extend(_collect_items(node.get("children") or [], include_secrets=include_secrets))
        elif node_type == "secret" and not include_secrets:
            continue
        else:
            result.append(node)
    return result


def _check_dest_permissions(dest: Path, reveal_secrets: bool) -> None:
    if not dest.exists():
        return
    if not reveal_secrets:
        return
    # Refuse to write revealed secrets into group/world-readable directories
    mode = dest.stat().st_mode
    import stat

    if mode & (stat.S_IRGRP | stat.S_IROTH):
        err(
            f"Refusing to write revealed secrets into {dest}: "
            "directory is group- or world-readable. "
            "Run: chmod 700 " + str(dest)
        )
        raise SystemExit(1)


def _safe_join(base: Path, name: str) -> Path:
    if os.path.isabs(name):
        raise ValueError(f"Absolute path in server response: {name!r}")
    resolved = (base / name).resolve()
    if not str(resolved).startswith(str(base.resolve())):
        raise ValueError(f"Path traversal: {name!r} escapes {base}")
    return base / name


def _atomic_write_text(path: Path, content: str, *, mode: int = 0o644) -> None:
    tmp = Path(str(path) + ".tmp")
    try:
        with tmp.open("w") as f:
            f.write(content)
        os.chmod(tmp, mode)
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
