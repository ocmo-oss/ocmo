#!/usr/bin/env python3
"""Comprehensive OCMO SDK example — one usage sample per API operation.

Runnable against the local docker stack (``OCMO_SERVER=http://localhost:8080``).
Reads from ``my-first-namespace``; mutations use ephemeral ``_sdk-demo/`` paths and
a throwaway namespace, cleaned up in ``finally``.

Operations covered (``sdk/operations.yaml`` + hand-written resolve):

* **System:** ``health``, ``version``, ``version_info`` (client helper)
* **Auth:** ``whoami``, ``can_i``
* **Namespaces:** ``list_namespaces``, ``show_namespace``, ``create_namespace``,
  ``update_namespace``, ``delete_namespace``
* **Schemas:** ``get_config_metadata_schema``, ``get_config_data_schema``,
  ``get_resolver_configuration_schema``, ``list_cast_formats``
* **Global permissions:** ``list_global_permissions``, ``create_global_permission``,
  ``get_global_permission``, ``update_global_permission``, ``move_global_permission``,
  ``delete_global_permission``
* **Global audit:** ``list_global_audit``, ``get_global_audit_event``
* **Tree:** ``navigate_root``, ``navigate_path``, ``search_root``, ``search_path``,
  ``get_item``, ``list_item_versions``, ``diff_item``, ``describe_item``,
  ``set_tag``, ``copy_item``, ``move_item``, ``delete_item``
* **Documents:** ``create_config``, ``update_config``, ``create_template``,
  ``update_template``, ``create_secret``, ``update_secret``
* **Resolvers:** ``create_resolver``, ``update_resolver``, ``rotate_resolver_token``
* **Resolve:** ``resolve`` (hand-written), ``resolve_parameters``, ``resolve_draft_config``,
  artifact ``bytes`` / ``text`` / ``data`` / ``open`` / ``save`` / ``save_all``
* **Propagation:** ``propagate_config``
* **Locks:** ``list_locks``, ``get_lock``, ``create_lock``, ``replace_lock``, ``delete_lock``
* **Audit:** ``list_namespace_audit``, ``get_namespace_audit_event``,
  ``namespace_audit_timeline``, ``namespace_audit_resolve_series``
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ocmo import (
    OcmoAPIError,
    OcmoClient,
    OcmoNotFoundError,
    OcmoPermissionError,
    OcmoValidationError,
)

NS = "my-first-namespace"
DEMO = "_sdk-demo"
TEMP_NS = f"sdk-demo-{uuid.uuid4().hex[:8]}"

# Existing paths in my-first-namespace (see namespace tree):
CFG = "tagtest/cfg"
PARAM_CFG = "test/dsfdaaa"
TEMPLATE = "test/template.j2"
RESOLVER = "test/resolver"
PROPAGATE_ROOT = "propagate"

# Plain dicts — SDK coerces these into generated payload models internally.
_DEMO_READ_PERMISSION = {
    "actors": [{"kind": "User", "claims": {"email": "*"}}],
}


def _section(title: str) -> None:
    print(f"\n── {title} " + "─" * max(0, 58 - len(title)))


def demo_system(client: OcmoClient) -> None:
    _section("System")
    print("health:", client.health().status)
    print("version:", client.version().version)
    print("version_info:", client.version_info())


def demo_auth(client: OcmoClient) -> None:
    _section("Auth")
    who = client.whoami()
    print(f"whoami: {who.display_name} ({who.user_details.email})")
    allowed = client.can_i(
        namespace=NS,
        resource=CFG,
        operations=["config:read", "config:write", "config:tag"],
    )
    print(f"can_i {CFG}:", allowed.allowed.additional_properties)


def demo_namespaces(client: OcmoClient) -> str | None:
    _section("Namespaces")
    namespaces = client.list_namespaces(limit=20)
    print("list_namespaces:", [ns.name for ns in namespaces.items][:5], "...")

    ns_info = client.show_namespace(NS)
    print(f"show_namespace {NS}:", ns_info.description or "(no description)")

    original_description = ns_info.description or ""
    client.update_namespace(NS, description="(touched by sdk/examples/sdk.py)")
    client.update_namespace(NS, description=original_description)
    print(f"update_namespace {NS}: ok")

    try:
        client.create_namespace(name=TEMP_NS, description="SDK example scratch namespace")
        print(f"create_namespace: {TEMP_NS}")
        return TEMP_NS
    except OcmoPermissionError as exc:
        print(f"create_namespace: skipped ({exc})")
        return None


def demo_schemas(client: OcmoClient, ns: str) -> None:
    _section("Schemas")
    meta = client.get_config_metadata_schema()
    print("get_config_metadata_schema keys:", list(meta.additional_properties.keys())[:4], "...")
    try:
        data_schema = client.ns(ns).get_config_data_schema(CFG)
        print(f"get_config_data_schema {CFG}:", type(data_schema).__name__)
    except OcmoNotFoundError:
        print(f"get_config_data_schema {CFG}: no per-config schema defined")
    resolver_schema = client.get_resolver_configuration_schema()
    print("get_resolver_configuration_schema:", type(resolver_schema).__name__)
    formats = client.list_cast_formats()
    print("list_cast_formats:", [f.format_ for f in formats.formats][:6])


def demo_global_permissions(client: OcmoClient) -> uuid.UUID | None:
    _section("Global permissions")
    existing = client.list_global_permissions(limit=5)
    print(f"list_global_permissions: {existing.count} rule(s)")

    if existing.rules:
        sample_id = existing.rules[0].id
        fetched = client.get_global_permission(sample_id)
        print(
            "get_global_permission:",
            fetched.rule.additional_properties.get("namespace", fetched.id),
        )

    rule_ns = f"sdk-demo-{uuid.uuid4().hex[:6]}-*"

    rule_id: uuid.UUID | None = None
    try:
        created = client.create_global_permission(namespace=rule_ns, read=_DEMO_READ_PERMISSION)
        rule_id = created.id
        print(f"create_global_permission: {rule_id}")

        client.update_global_permission(
            rule_id,
            namespace=rule_ns,
            description="SDK example rule",
            read=_DEMO_READ_PERMISSION,
        )
        print("update_global_permission: ok")

        client.move_global_permission(rule_id, position=created.position + 0.5)
        print("move_global_permission: ok")
    except (OcmoPermissionError, OcmoValidationError) as exc:
        print(f"global permission mutations: skipped ({exc})")

    return rule_id


def demo_global_audit(client: OcmoClient) -> None:
    _section("Global audit")
    audit = client.list_global_audit(limit=3)
    print(f"list_global_audit: {len(audit.items)} event(s)")
    if audit.items:
        event = client.get_global_audit_event(audit.items[0].id)
        print(f"get_global_audit_event: {event.event_kind} {event.operation or ''}")


def demo_tree_read(client: OcmoClient) -> None:
    _section("Tree (read)")
    ns = client.ns(NS)
    root = ns.navigate_root(limit=50)
    user_items = [c.path for c in root.children if not c.path.startswith("_")]
    print("navigate_root:", user_items[:6], "...")

    test_folder = ns.navigate_path("test")
    print("navigate_path test/:", [c.path for c in test_folder.children][:5])

    hits = ns.search_root(q="cfg", limit=10)
    print("search_root cfg:", [h.path for h in hits.items])

    sub_hits = ns.search_path("test", q="template", limit=5)
    print("search_path test/ template:", [h.path for h in sub_hits.items])

    cfg = ns.get_item(CFG)
    print(f"get_item {CFG}:", cfg.version_data.data.strip())
    print(f"  tags: {list(cfg.tags.additional_properties.keys())}")

    versions = ns.list_item_versions(CFG, limit=5)
    print(f"list_item_versions {CFG}:", versions.versions_count, "version(s)")

    diff = ns.diff_item(CFG, from_="latest", to="latest")
    print(f"diff_item {CFG}: identical={diff.identical}")


def demo_resolve(client: OcmoClient) -> None:
    _section("Resolve")
    ns = client.ns(NS)

    result = ns.resolve(CFG, cast="python")
    print(f"resolve {CFG}: cache={result.cache_status}, items={len(result)}")
    item = result["cfg"]
    print(f"  artifact checksum={item.checksum[:12]}… parsed={item.data}")

    with item.open() as resp:
        streamed = sum(len(chunk) for chunk in resp.iter_bytes())
    print(f"  open() streamed {streamed} byte(s)")

    param_result = ns.resolve(PARAM_CFG, cast="yaml")
    print(f"resolve {PARAM_CFG}:", param_result["dsfdaaa"].text.splitlines()[0])

    folder = ns.resolve("tagtest", cast="json")
    print("resolve tagtest/:", [i.name for i in folder])

    trace = ns.resolve(CFG, cast="json", trace_only=True)
    print(f"resolve trace_only: items={len(trace)}, trace_only={trace.trace_only}")

    params = ns.resolve_parameters(PARAM_CFG)
    print(f"resolve_parameters {PARAM_CFG}: v{params.version} ({params.requested_version})")

    draft = ns.resolve_draft_config(
        f"{DEMO}/draft.cfg",
        content="draft_key: from_draft\n",
        cast="yaml",
    )
    print(f"resolve_draft_config: {len(draft.items)} item(s)")

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        folder.save_all(out)
        item.save(out / "cfg.json")
        print(f"save_all + save → {list(out.iterdir())}")


def demo_propagate(client: OcmoClient) -> None:
    _section("Propagation")
    ns = client.ns(NS)
    try:
        children = ns.navigate_path(PROPAGATE_ROOT, limit=20).children
        source = next((c.path for c in children if c.node_type == "config"), None)
        if source:
            plan = ns.propagate_config(source)
            print(f"propagate_config {source}: {len(plan.targets)} target(s)")
        else:
            print(f"propagate_config: no config under {PROPAGATE_ROOT}/ (skipped)")
    except OcmoNotFoundError:
        print(f"propagate_config: {PROPAGATE_ROOT}/ not found (skipped)")


def demo_locks(client: OcmoClient) -> None:
    _section("Locks")
    ns = client.ns(NS)
    locks = ns.list_locks(limit=50)
    print(f"list_locks: {locks.count} active")
    for lock in locks.locks[:3]:
        print(f"  {lock.path} — {lock.reason}")

    lock_path = f"{DEMO}/app.cfg"
    created = ns.create_lock(lock_path, reason="SDK example lock")
    print(f"create_lock {lock_path}: {created.reason}")

    current = ns.get_lock(lock_path)
    print(f"get_lock {lock_path}: by {current.locked_by}")

    ns.replace_lock(lock_path, reason="SDK example lock (replaced)")
    print("replace_lock: ok")

    ns.delete_lock(lock_path)
    print("delete_lock: ok")


def demo_namespace_audit(client: OcmoClient) -> None:
    _section("Namespace audit")
    ns = client.ns(NS)
    audit = ns.list_namespace_audit(limit=5)
    print(f"list_namespace_audit: {len(audit.items)} event(s)")
    for event in audit.items[:3]:
        print(
            f"  {event.occurred_at:%Y-%m-%d %H:%M} "
            f"{event.event_kind} {event.operation or ''} "
            f"{event.object_type or ''}/{event.object_id or ''}"
        )

    if audit.items:
        detail = ns.get_namespace_audit_event(audit.items[0].id)
        print(f"get_namespace_audit_event: {detail.event_kind}")

    timeline = ns.namespace_audit_timeline(object_id=CFG, object_type="config", limit=5)
    print(f"namespace_audit_timeline {CFG}: {len(timeline.items)} point(s)")

    series = ns.namespace_audit_resolve_series(
        object_id=CFG,
        object_type="config",
        from_=datetime.now(timezone.utc) - timedelta(days=1),
        to=datetime.now(timezone.utc),
        bucket_seconds=3600,
    )
    print(f"namespace_audit_resolve_series: {len(series.buckets)} bucket(s)")


def demo_mutations(client: OcmoClient) -> list[str]:
    """Create scratch items; return paths to delete in cleanup."""
    _section("Mutations (scratch)")
    ns = client.ns(NS)
    created: list[str] = []

    cfg = f"{DEMO}/app.cfg"
    ns.create_config(cfg, content="demo_key: one\n")
    ns.update_config(cfg, content="demo_key: two\n")
    created.append(cfg)
    print(f"create_config + update_config: {cfg}")

    ns.describe_item(cfg, description="SDK demo config")
    print("describe_item: ok")

    ns.set_tag(cfg, tag="sdk-demo", version=2)
    print("set_tag sdk-demo: ok")

    ns.diff_item(cfg, from_="1", to="latest")
    print("diff_item v1→latest: ok")

    tmpl = f"{DEMO}/tmpl.j2"
    ns.create_template(tmpl, content="hello: {{ name }}\n")
    ns.update_template(tmpl, content="hello: {{ name | upper }}\n")
    created.append(tmpl)
    print(f"create_template + update_template: {tmpl}")

    secret = f"{DEMO}/secret.yaml"
    ns.create_secret(secret, content="user: demo\npassword: changeme\n")
    ns.update_secret(secret, content="user: demo\npassword: rotated\n")
    created.append(secret)
    print(f"create_secret + update_secret: {secret}")

    resolver = f"{DEMO}/resolver"
    try:
        ns.create_resolver(resolver, content="{}")
        ns.update_resolver(resolver, content="{}")
        ns.rotate_resolver_token(resolver, token_number=1)
        created.append(resolver)
        print(
            "create_resolver + update_resolver + rotate_resolver_token:",
            resolver,
        )
    except OcmoAPIError as exc:
        print(f"resolver ops: skipped ({exc})")

    copy_path = f"{DEMO}/app-copy.cfg"
    ns.copy_item(cfg, target_path=copy_path, tag_to_copy="latest")
    created.append(copy_path)
    print(f"copy_item → {copy_path}")

    moved = f"{DEMO}/moved.cfg"
    ns.move_item(copy_path, target_path=moved)
    created.append(moved)
    print(f"move_item → {moved}")

    preview = ns.delete_item(moved, preview=True)
    print(f"delete_item preview {moved}: would delete {len(preview.delete)} object(s)")

    try:
        ns.set_tag(cfg, body={"tag": "sdk-demo", "version": None})
        print("untag sdk-demo: ok")
    except OcmoAPIError as exc:
        print(f"untag: skipped ({type(exc).__name__})")

    ns.resolve(cfg, cast="json", mark_stable=True)
    print(f"resolve mark_stable {cfg}: ok")

    return created


def demo_errors(client: OcmoClient) -> None:
    _section("Errors")
    try:
        client.ns(NS).get_item("does-not-exist")
    except OcmoNotFoundError as exc:
        print(f"OcmoNotFoundError: {exc.message}")

    try:
        client.delete_namespace("does-not-exist-namespace")
    except OcmoNotFoundError as exc:
        print(f"delete_namespace (missing): {exc.message}")


def cleanup(
    client: OcmoClient,
    *,
    demo_paths: list[str],
    temp_ns: str | None,
    global_rule_id: uuid.UUID | None,
) -> None:
    _section("Cleanup")
    ns = client.ns(NS)
    for path in reversed(demo_paths):
        try:
            ns.delete_item(path, preview=False)
            print(f"delete_item {path}: ok")
        except OcmoNotFoundError:
            pass
    try:
        ns.delete_item(DEMO, preview=False)
        print(f"delete_item {DEMO}/: ok")
    except OcmoNotFoundError:
        pass

    if global_rule_id is not None:
        try:
            client.delete_global_permission(global_rule_id)
            print(f"delete_global_permission {global_rule_id}: ok")
        except Exception as exc:  # noqa: BLE001 — best-effort demo cleanup
            print(f"delete_global_permission: skipped ({exc})")

    if temp_ns:
        try:
            client.delete_namespace(temp_ns)
            print(f"delete_namespace {temp_ns}: ok")
        except Exception as exc:  # noqa: BLE001
            print(f"delete_namespace: skipped ({exc})")


def main() -> None:
    demo_paths: list[str] = []
    temp_ns: str | None = None
    global_rule_id: uuid.UUID | None = None

    with OcmoClient() as client:
        try:
            demo_system(client)
            demo_auth(client)
            temp_ns = demo_namespaces(client)
            demo_schemas(client, NS)
            global_rule_id = demo_global_permissions(client)
            demo_global_audit(client)
            demo_tree_read(client)
            demo_resolve(client)
            demo_propagate(client)
            demo_paths = demo_mutations(client)
            demo_locks(client)
            demo_namespace_audit(client)
            demo_errors(client)
        finally:
            cleanup(
                client,
                demo_paths=demo_paths,
                temp_ns=temp_ns,
                global_rule_id=global_rule_id,
            )


if __name__ == "__main__":
    main()
