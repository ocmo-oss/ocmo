"""ocmo import — import a directory tree into OCMO.

Classification:
  parseable YAML/JSON object → Config
  everything else          → Template

With ``--from-metadata``, each file's export metadata (xattrs or comment headers)
selects the target namespace path and item type.

Slug rule: NFC-normalise, replace forbidden chars with '-', trim '-', preserve case.
The .ocmoignore file (gitignore syntax) and --exclude control what is walked.
"""

from __future__ import annotations

import fnmatch
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from .._address import slug
from .._client import OcmoCtx
from .._errors import sdk_command
from .._exit import USAGE_ERROR, VERIFY_FAILURE
from .._import_metadata import import_file_text, read_file_metadata
from .._import_plan import (
    annotate_plan_conflicts,
    build_metadata_entry,
    load_type_map,
    parse_type_override,
    resolve_import_type,
    try_parse_config_document,
)
from .._options import dry_run_option, yes_option
from .._output import as_dict, confirm, emit_table, err, warn

if TYPE_CHECKING:
    from ocmo import NamespaceView


@click.command("import")
@click.argument("source_dir")
@click.option("--to", "target_path", default=None, metavar="PATH", help="Target tree path prefix to import into.")
@click.option("-n", "--namespace", default=None)
@click.option(
    "--from-metadata",
    is_flag=True,
    default=False,
    help="Import items using export metadata (namespace/path) from files.",
)
@dry_run_option()
@click.option("--verify", is_flag=True, default=False, help="After import, resolve and compare against source.")
@click.option(
    "--update",
    is_flag=True,
    default=False,
    help="Update existing items (create a new version). Otherwise, conflicts fail.",
)
@click.option(
    "--exclude", "excludes", multiple=True, metavar="GLOB", help="Glob patterns to exclude (may be repeated)."
)
@click.option(
    "--type-override",
    "type_override_specs",
    multiple=True,
    metavar="GLOB=TYPE",
    help="Force item type for matching paths (config|template|secret|resolver).",
)
@click.option(
    "--type-map",
    "type_map_path",
    default=None,
    type=click.Path(exists=True),
    help="YAML file mapping glob patterns to item types.",
)
@click.option(
    "--on-conflict", type=click.Choice(["fail", "suffix"]), default="fail", help="How to handle slug collisions."
)
@click.option(
    "--merge-metadata", is_flag=True, default=False, help="Allow merging into files that already have the metadata key."
)
@click.option("--follow-symlinks", is_flag=True, default=False)
@yes_option()
@click.pass_obj
@sdk_command
def import_cmd(
    ctx: OcmoCtx,
    source_dir: str,
    target_path: str | None,
    namespace: str | None,
    from_metadata: bool,
    dry_run: bool,
    verify: bool,
    update: bool,
    excludes: tuple[str, ...],
    type_override_specs: tuple[str, ...],
    type_map_path: str | None,
    on_conflict: str,
    merge_metadata: bool,
    follow_symlinks: bool,
    yes: bool,
) -> None:
    """Import a directory tree into OCMO.

    \b
    Examples:
      ocmo -n prod import ./configs/ --to app/ --dry-run
      ocmo -n prod import ./configs/ --to app/
      ocmo -n prod import ./backup/ --from-metadata --update
    """
    source = Path(source_dir).resolve()
    if not source.is_dir():
        err(f"Source directory not found: {source}")
        raise SystemExit(1)

    if not from_metadata and not target_path:
        err("--to is required unless --from-metadata is set.")
        raise SystemExit(USAGE_ERROR)

    ns = ctx.require_namespace(namespace)
    view = ctx.namespace_view(namespace)
    metadata_key = _get_metadata_key(ctx)
    ignore_patterns = _load_ocmoignore(source) + list(excludes)
    type_map, type_overrides = _load_type_rules(type_map_path, type_override_specs)

    plan = _build_plan(
        source=source,
        target_base=target_path or "",
        ignore_patterns=ignore_patterns,
        from_metadata=from_metadata,
        follow_symlinks=follow_symlinks,
        metadata_key=metadata_key,
        merge_metadata=merge_metadata,
        on_conflict=on_conflict,
        namespace=ns,
        type_map=type_map,
        type_overrides=type_overrides,
    )

    if not plan:
        warn("No files to import.")
        return

    conflicts = annotate_plan_conflicts(
        plan,
        namespace=ns,
        update=update,
        view=view,
    )

    if dry_run or ctx.dry_run:
        from .._dry_run import emit_dry_run_plan, format_import_dry_run_header  # deferred

        emit_dry_run_plan(format_import_dry_run_header(len(plan)))
        emit_table(
            [
                {
                    "source": str(entry["source_rel"]),
                    "type": entry["kind"],
                    "path": entry["tree_path"],
                    "action": entry.get("action", "create"),
                    "status": entry.get("status", "ok"),
                }
                for entry in plan
            ],
            columns=["source", "type", "path", "action", "status"],
        )
        if conflicts:
            err("Import blocked by conflicts:")
            for message in conflicts:
                err(f"  {message}")
            raise SystemExit(USAGE_ERROR)
        return

    created = updated = skipped = failed = 0

    for entry in plan:
        if entry.get("status") == "conflict":
            warn(f"Skipping {entry['source_rel']}: {entry.get('conflict')}")
            skipped += 1
            continue

        kind = entry["kind"]
        tree_path = entry["tree_path"]
        content: str = entry["content"]

        if not (yes or ctx.yes) and kind == "secret":
            if not confirm(f"Import secret {tree_path!r}?", yes=False):
                skipped += 1
                continue

        try:
            if kind == "config":
                _import_item(view, "config", tree_path, content, update=update)
            elif kind == "template":
                _import_item(view, "template", tree_path, content, update=update)
            elif kind == "secret":
                _import_item(view, "secret", tree_path, content, update=update)
            elif kind == "resolver":
                _import_item(view, "resolver", tree_path, content, update=update)
            else:
                warn(f"Skipping unsupported type {kind!r} at {tree_path!r}.")
                skipped += 1
                continue

            created += 1
        except Exception as exc:
            msg = str(exc)
            if "already exists" in msg.lower() or "conflict" in msg.lower():
                if update:
                    updated += 1
                else:
                    warn(f"Conflict at {tree_path!r}: {exc} (use --update to overwrite)")
                    skipped += 1
            else:
                warn(f"Failed {tree_path!r}: {exc}")
                failed += 1

    print(
        f"Import complete: created={created}, updated={updated}, " f"skipped={skipped}, failed={failed}.",
        file=sys.stderr,
    )

    if verify and not failed:
        _run_verify(
            view,
            source,
            target_path or "",
            plan,
            metadata_key=metadata_key,
        )


# ---------------------------------------------------------------------------
# Plan building
# ---------------------------------------------------------------------------


def _build_plan(
    *,
    source: Path,
    target_base: str,
    ignore_patterns: list[str],
    from_metadata: bool,
    follow_symlinks: bool,
    metadata_key: str,
    merge_metadata: bool,
    on_conflict: str,
    namespace: str,
    type_map: list[tuple[str, str]],
    type_overrides: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    slug_set: set[str] = set()

    for file_path in _walk(source, ignore_patterns=ignore_patterns, follow_symlinks=follow_symlinks):
        rel = file_path.relative_to(source)
        rel_str = str(rel)
        content_bytes = file_path.read_bytes()

        if from_metadata:
            if not read_file_metadata(file_path).get("path"):
                continue
            entry = build_metadata_entry(
                file_path=file_path,
                rel=rel,
                rel_str=rel_str,
                target_prefix=target_base,
                content_bytes=content_bytes,
                type_map=type_map,
                type_overrides=type_overrides,
            )
            if entry is None:
                continue
            plan.append(entry)
            continue

        kind = resolve_import_type(
            rel_str,
            type_map=type_map,
            type_overrides=type_overrides,
            metadata_type=None,
            content_bytes=content_bytes,
        )
        tree_path = _build_tree_path(rel, target_base)

        slug_key = tree_path.lower()
        if slug_key in slug_set:
            if on_conflict == "fail":
                err(f"Slug collision: {rel_str!r} → {tree_path!r} already mapped.")
                raise SystemExit(USAGE_ERROR)
            tree_path = _add_suffix(tree_path)
        slug_set.add(slug_key)

        if kind == "config":
            content, conflict = _prepare_config_content(
                content_bytes=content_bytes,
                rel_str=rel_str,
                tree_path=tree_path,
                metadata_key=metadata_key,
                merge_metadata=merge_metadata,
            )
            entry = {
                "kind": "config",
                "source_rel": rel,
                "source_abs": file_path,
                "tree_path": tree_path,
                "content": content,
            }
            if conflict:
                entry["conflict_reason"] = conflict
            plan.append(entry)
        elif kind in ("secret", "resolver"):
            plan.append(
                {
                    "kind": kind,
                    "source_rel": rel,
                    "source_abs": file_path,
                    "tree_path": tree_path,
                    "content": import_file_text(content_bytes),
                }
            )
        elif kind == "template":
            plan.append(
                {
                    "kind": "template",
                    "source_rel": rel,
                    "source_abs": file_path,
                    "tree_path": tree_path,
                    "content": import_file_text(content_bytes),
                }
            )

    return plan


def _load_type_rules(
    type_map_path: str | None,
    type_override_specs: tuple[str, ...],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    type_map: list[tuple[str, str]] = []
    if type_map_path:
        try:
            type_map = load_type_map(Path(type_map_path))
        except ValueError as exc:
            err(str(exc))
            raise SystemExit(USAGE_ERROR)

    type_overrides: list[tuple[str, str]] = []
    for spec in type_override_specs:
        try:
            type_overrides.append(parse_type_override(spec))
        except ValueError as exc:
            err(str(exc))
            raise SystemExit(USAGE_ERROR)

    return type_map, type_overrides


def _build_tree_path(rel: Path, target_base: str) -> str:
    base = target_base.rstrip("/")
    parts = [slug(p) for p in rel.parts]
    return base + "/" + "/".join(parts)


def _prepare_config_content(
    *,
    content_bytes: bytes,
    rel_str: str,
    tree_path: str,
    metadata_key: str,
    merge_metadata: bool,
) -> tuple[str, str | None]:
    import yaml  # deferred

    text = import_file_text(content_bytes)
    doc, is_json = try_parse_config_document(text.encode("utf-8"))
    if doc is None:
        return text, None

    if metadata_key in doc and not merge_metadata:
        return "", (f"file already contains key {metadata_key!r} " "(use --merge-metadata to override)")

    meta: dict[str, Any] = {}
    slugged = tree_path.split("/")[-1]
    if slugged != rel_str:
        meta["name"] = rel_str
    if is_json:
        meta["cast"] = {"format": "json"}

    if meta:
        existing = doc.get(metadata_key, {})
        if not isinstance(existing, dict):
            existing = {}
        doc[metadata_key] = {**existing, **meta}

    if is_json:
        return json.dumps(doc, indent=2), None
    return yaml.safe_dump(doc, default_flow_style=False), None


def _add_suffix(path: str) -> str:
    parts = path.rsplit("/", 1)
    return parts[0] + "/" + parts[1] + "_1" if len(parts) == 2 else path + "_1"


# ---------------------------------------------------------------------------
# Import helpers
# ---------------------------------------------------------------------------


def _get_metadata_key(ctx: OcmoCtx) -> str:
    try:
        info = ctx.client().version()  # type: ignore[no-untyped-call]
        data = as_dict(info)
        return data.get("config_metadata_key") or "_ocmo"
    except Exception:
        return "_ocmo"


def _import_item(
    view: NamespaceView,
    kind: str,
    path: str,
    content: str,
    *,
    update: bool,
) -> None:
    methods = {
        "config": (view.update_config, view.create_config),
        "template": (view.update_template, view.create_template),
        "secret": (view.update_secret, view.create_secret),
        "resolver": (view.update_resolver, view.create_resolver),
    }
    update_fn, create_fn = methods[kind]
    try:
        update_fn(path=path, content=content)
    except Exception:
        create_fn(path=path, content=content)


# ---------------------------------------------------------------------------
# Filesystem walk
# ---------------------------------------------------------------------------


def _walk(
    root: Path,
    *,
    ignore_patterns: list[str],
    follow_symlinks: bool,
) -> list[Path]:
    results: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        dp = Path(dirpath)
        rel_dir = dp.relative_to(root)

        dirnames[:] = [d for d in dirnames if d != ".git"]

        for filename in sorted(filenames):
            rel_file = rel_dir / filename
            rel_str = str(rel_file)

            full = dp / filename
            if full.is_symlink() and not follow_symlinks:
                warn(f"Skipping symlink: {rel_str}")
                continue

            if _is_ignored(rel_str, ignore_patterns):
                continue

            results.append(full)

    return results


def _is_ignored(rel_str: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(rel_str, pat) or fnmatch.fnmatch(Path(rel_str).name, pat):
            return True
    return False


def _load_ocmoignore(root: Path) -> list[str]:
    ignore_file = root / ".ocmoignore"
    if not ignore_file.exists():
        return []
    patterns: list[str] = []
    for line in ignore_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


# ---------------------------------------------------------------------------
# Verification (§12.3)
# ---------------------------------------------------------------------------


def _run_verify(
    view: NamespaceView,
    source: Path,
    target_path: str,
    plan: list[dict[str, Any]],
    *,
    metadata_key: str,
) -> None:
    """Resolve the imported folder and compare against the source directory."""
    import tempfile

    from .._resolve_write import write_resolve_items

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        try:
            result = view.resolve(target_path.rstrip("/") + "/")
            items = list(result)
            outcomes = write_resolve_items(
                items,  # type: ignore[arg-type]  # SDK ResolvedItem satisfies ResolvedArtifact
                output_dir=str(tmp),
                rewrite=True,
            )
        except Exception as exc:
            err(f"Verify: resolve failed: {exc}")
            raise SystemExit(VERIFY_FAILURE)

        write_failures = [o for o in outcomes if o.result == "failed"]
        if write_failures:
            err("Verify: failed to write resolved output:")
            for outcome in write_failures:
                detail = outcome.detail or "write failed"
                err(f"  {outcome.path}: {detail}")
            raise SystemExit(VERIFY_FAILURE)

        mismatches: list[str] = []
        for entry in plan:
            if entry["kind"] != "config":
                continue
            rel = _expected_verify_rel(entry, target_path)
            src_text = import_file_text(entry["source_abs"].read_bytes())
            resolved_file = tmp / rel
            if not resolved_file.exists():
                mismatches.append(f"MISSING: {rel}")
                continue
            try:
                src_doc, _ = try_parse_config_document(src_text.encode("utf-8"))
                res_doc, _ = try_parse_config_document(
                    resolved_file.read_bytes(),
                )
                if src_doc is None or res_doc is None:
                    if resolved_file.read_text(encoding="utf-8") != src_text:
                        mismatches.append(f"BYTE MISMATCH: {rel}")
                    continue
                src_body = _config_document_body(src_doc, metadata_key)
                res_body = _config_document_body(res_doc, metadata_key)
                if src_body != res_body:
                    mismatches.append(f"SEMANTIC MISMATCH: {rel}")
            except Exception as e:
                mismatches.append(f"PARSE ERROR: {rel}: {e}")

        if mismatches:
            err("Verification failed:")
            for m in mismatches:
                err(f"  {m}")
            raise SystemExit(VERIFY_FAILURE)
        else:
            print("Verification passed.", file=sys.stderr)


def _expected_verify_rel(entry: dict[str, Any], target_path: str) -> str:
    """Path of a resolved artifact relative to the verify output directory."""
    tree_path = str(entry["tree_path"]).strip("/")
    base = target_path.strip("/")
    if base and (tree_path == base or tree_path.startswith(f"{base}/")):
        if tree_path == base:
            return Path(tree_path).name
        return str(tree_path[len(base) + 1 :])
    return str(entry["source_rel"])


def _config_document_body(
    doc: dict[str, Any] | None,
    metadata_key: str,
) -> dict[str, Any] | None:
    if doc is None:
        return None
    body = dict(doc)
    body.pop(metadata_key, None)
    return body
