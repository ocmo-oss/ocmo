#!/usr/bin/env python3
"""Generate ocmo/_facade_impl.py and ocmo/_facade_meta.py from sdk/operations.yaml."""

from __future__ import annotations

import ast
import importlib
import re
from pathlib import Path
from typing import Any

import attrs
import yaml

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "ocmo" / "_generated" / "api"
OPERATIONS = ROOT / "operations.yaml"
OUT_IMPL = ROOT / "ocmo" / "_facade_impl.py"
OUT_META = ROOT / "ocmo" / "_facade_meta.py"

DEFAULT_PAGE_SIZE = 100

# OpenAPI list endpoints: (items_field, total_count_field)
PAGINATED_OPS: dict[str, tuple[str, str]] = {
    "list_namespaces": ("items", "count"),
    "list_global_permissions": ("rules", "count"),
    "list_global_audit": ("items", "count"),
    "list_namespace_audit": ("items", "count"),
    "list_locks": ("locks", "count"),
    "namespace_audit_timeline": ("items", "count"),
    "navigate_root": ("children", "children_count"),
    "navigate_path": ("children", "children_count"),
    "search_root": ("items", "count"),
    "search_path": ("items", "count"),
    "list_item_versions": ("versions", "versions_count"),
}

DOCUMENT_BODY_OPS = frozenset(
    {
        "create_config",
        "update_config",
        "create_template",
        "update_template",
        "create_secret",
        "update_secret",
        "create_resolver",
        "update_resolver",
        "resolve_draft_config",
    }
)


def _camel_to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _parse_sync(path: Path) -> tuple[list[str], list[str], str | None] | None:
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "sync":
            pos = [a.arg for a in node.args.args]
            kw = [a.arg for a in node.args.kwonlyargs if a.arg != "client"]
            body_ann = None
            for arg in node.args.kwonlyargs:
                if arg.arg == "body" and arg.annotation is not None:
                    body_ann = ast.unparse(arg.annotation)
            return pos, kw, body_ann
    return None


def _find_generated_module(operation_id: str) -> Path | None:
    matches = list(API_DIR.rglob(f"{operation_id}.py"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"ambiguous generated module for {operation_id!r}: {matches}")
    return None


def _import_stmt(module_path: Path, operation_id: str) -> str:
    rel = module_path.relative_to(API_DIR).with_suffix("")
    parts = list(rel.parts)
    import_path = "ocmo._generated.api." + ".".join(parts)
    alias = operation_id.replace("-", "_")
    return f"import {import_path} as _op_{alias}"


def _resolve_body_payload(body_ann: str | None) -> tuple[str, str, list[str]] | None:
    if not body_ann:
        return None
    if "Union" in body_ann and "str" in body_ann:
        return None
    match = re.search(r"(\w+Payload|\w+Schema)\b", body_ann)
    if not match:
        return None
    class_name = match.group(1)
    module = f"ocmo._generated.models.{_camel_to_snake(class_name)}"
    cls = getattr(importlib.import_module(module), class_name)
    fields = [f.name for f in attrs.fields(cls) if f.name != "additional_properties"]
    return module, class_name, fields


def _public_kw(
    kw: list[str],
    *,
    operation_id: str,
    body_spec: tuple[str, str, list[str]] | None,
) -> list[str]:
    out: list[str] = []
    body_fields: set[str] = set(body_spec[2]) if body_spec else set()
    is_document = operation_id in DOCUMENT_BODY_OPS

    for name in kw:
        if name == "body":
            continue
        out.append(name)

    if is_document:
        out.append("content")
    elif body_spec:
        for field in body_spec[2]:
            if field not in out:
                out.append(field)

    if body_spec or is_document:
        out.append("body")

    return out


def _signature(
    pos: list[str],
    kw: list[str],
    *,
    bind_namespace: bool,
    operation_id: str,
    body_spec: tuple[str, str, list[str]] | None,
) -> tuple[str, str]:
    if bind_namespace:
        pos = pos[1:]

    public_kw = _public_kw(kw, operation_id=operation_id, body_spec=body_spec)

    def_parts: list[str] = []
    call_parts: list[str] = []
    for p in pos:
        def_parts.append(f"{p}: Any")
        call_parts.append(f"{p}")

    kw_parts: list[str] = []
    for p in public_kw:
        if p == "from_":
            kw_parts.append("from_: Any = UNSET")
            call_parts.append("from_=from_")
        else:
            kw_parts.append(f"{p}: Any = UNSET")
            call_parts.append(f"{p}={p}")

    if bind_namespace:
        call_parts = ["self._namespace", *call_parts]

    if def_parts and kw_parts:
        full_def = f"{', '.join(def_parts)}, *, {', '.join(kw_parts)}"
    elif kw_parts:
        full_def = f"*, {', '.join(kw_parts)}"
    else:
        full_def = ", ".join(def_parts)

    call_sig = ", ".join(call_parts)
    return full_def, call_sig


def _emit_ops(class_name: str, ops: list[dict], *, async_: bool) -> str:
    lines = [f"class {class_name}:"]
    executor = "execute_async" if async_ else "execute_sync"
    await_kw = "await " if async_ else ""

    for op in ops:
        full_def, call_sig = _signature(
            op["pos"],
            op["kw"],
            bind_namespace=op["scope"] == "namespace",
            operation_id=op["operation_id"],
            body_spec=op.get("body_spec"),
        )
        alias = f"_op_{op['method'].replace('-', '_')}"
        args_line = f"{call_sig},\n            " if call_sig else ""
        lines.append(f"    {'async ' if async_ else ''}def {op['method']}(self{', ' + full_def if full_def else ''}):")
        lines.append(f'        """OpenAPI operation ``{op["operation_id"]}``."""\n')
        lines.append(
            f"        return {await_kw}{executor}(\n"
            f'            "{op["operation_id"]}",\n'
            f"            {alias}.{'asyncio_detailed' if async_ else 'sync_detailed'},\n"
            f"            {args_line}"
            f"client=self._api,\n"
            f"        )"
        )
        lines.append("")
    return "\n".join(lines)


def _collect() -> tuple[list[dict], list[dict], dict[str, tuple[str, str, list[str]]]]:
    registry = yaml.safe_load(OPERATIONS.read_text())["operations"]
    client_ops: list[dict] = []
    ns_ops: list[dict] = []
    body_payloads: dict[str, tuple[str, str, list[str]]] = {}

    for operation_id, meta in sorted(registry.items()):
        if meta.get("sdk") is False:
            continue
        module_path = _find_generated_module(operation_id)
        if module_path is None:
            raise FileNotFoundError(f"no generated module for operation {operation_id!r}")
        parsed = _parse_sync(module_path)
        if parsed is None:
            raise ValueError(f"no sync() in {module_path}")
        pos, kw, body_ann = parsed
        method = meta.get("sdk_method", operation_id)
        scope = meta["scope"]
        body_spec = _resolve_body_payload(body_ann)
        if body_spec:
            body_payloads[operation_id] = body_spec
        op = {
            "operation_id": operation_id,
            "method": method,
            "module_path": module_path,
            "pos": pos,
            "kw": kw,
            "scope": scope,
            "body_spec": body_spec,
        }
        if scope == "namespace":
            ns_ops.append(op)
        elif scope == "client":
            client_ops.append(op)
        else:
            raise ValueError(f"unknown scope {scope!r} for {operation_id}")
    return client_ops, ns_ops, body_payloads


def _emit_meta(body_payloads: dict[str, tuple[str, str, list[str]]]) -> str:
    lines = [
        '"""AUTO-GENERATED by scripts/generate_facade.py — do not edit."""',
        "",
        "from __future__ import annotations",
        "",
        f"DEFAULT_PAGE_SIZE = {DEFAULT_PAGE_SIZE}",
        "",
        "PAGINATED: dict[str, tuple[str, str]] = {",
    ]
    for op_id, pair in sorted(PAGINATED_OPS.items()):
        lines.append(f'    "{op_id}": {pair!r},')
    lines.append("}")
    lines.append("")
    lines.append("DOCUMENT_BODY_OPS = frozenset(")
    lines.append("    {")
    for op_id in sorted(DOCUMENT_BODY_OPS):
        lines.append(f'        "{op_id}",')
    lines.append("    }")
    lines.append(")")
    lines.append("")
    lines.append("BODY_PAYLOADS: dict[str, tuple[str, str, list[str]]] = {")
    for op_id, spec in sorted(body_payloads.items()):
        lines.append(f'    "{op_id}": {spec!r},')
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    client_ops, ns_ops, body_payloads = _collect()

    imports = sorted({_import_stmt(op["module_path"], op["operation_id"]) for op in client_ops + ns_ops})

    header = '''\
"""AUTO-GENERATED by scripts/generate_facade.py — do not edit."""

from __future__ import annotations

from typing import Any

from ocmo._facade_runtime import execute_async, execute_sync
from ocmo._generated.types import UNSET

'''
    body = "\n".join(imports)
    body += "\n\n"
    body += _emit_ops("_ClientFacadeMixin", client_ops, async_=False)
    body += "\n\n"
    body += _emit_ops("_AsyncClientFacadeMixin", client_ops, async_=True)
    body += "\n\n"
    body += _emit_ops("_NamespaceFacadeMixin", ns_ops, async_=False)
    body += "\n\n"
    body += _emit_ops("_AsyncNamespaceFacadeMixin", ns_ops, async_=True)
    body += "\n"

    OUT_IMPL.write_text(header + body)
    OUT_META.write_text(_emit_meta(body_payloads))
    print(
        f"Wrote {OUT_IMPL} ({len(client_ops)} client ops, {len(ns_ops)} namespace ops) "
        f"and {OUT_META}"
    )


if __name__ == "__main__":
    main()
