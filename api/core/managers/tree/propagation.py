from ._common import *


class TreePropagationMixin:
    def propagation_handler(self, tag_name: str, version: int) -> Optional[dict]:
        """Run tag-triggered propagation when configured on this config path."""
        source_item = self.get_or_raise(["config"])
        source_version = self.resolve_version(source_item, str(version))
        metadata, _body = ConfigValidationManager.parse_config_yaml_document(source_version.data)
        rules = metadata.propagation
        if rules is None or not rules.enabled or rules.trigger != "tag":
            return None
        if not rules.tag or not fnmatch.fnmatch(tag_name, rules.tag):
            return None
        return self.propagate_config(version_ref=str(version), trigger="tag", trigger_tag=tag_name)

    @audit(
        "config",
        object_id_attr=lambda self: self.path,
        operation=OP_PROPAGATE_CONFIG,
        subresource_type="trigger",
    )
    def propagate_config(self, version_ref: str, *, trigger: str, trigger_tag: str = "") -> dict:
        """Resolve propagation targets and persist merged config versions."""

        source_item = self.get_or_raise(["config"])
        source_version = self.resolve_version(source_item, version_ref)
        source_metadata, source_body = ConfigValidationManager.parse_config_yaml_document(source_version.data)
        rules = source_metadata.propagation

        if source_metadata is None or rules is None or not rules.enabled:
            if trigger == "manual":
                raise PropagationNotConfigured(f"Propagation is not configured or disabled on config '{self.path}'")
            return self._finalize_propagate_config(
                source_version=source_version.version,
                trigger=trigger,
                trigger_tag=trigger_tag,
                target_results=[],
            )

        if trigger == "manual" and rules.trigger != "manual":
            raise PropagationNotConfigured(f"Propagation is not configured or disabled on config '{self.path}'")

        target_versions: list[PropagationTargetVersion] = []
        target_results: list[dict] = []

        for target_ref in rules.targets:
            target_path, target_version_ref = parse_ref(target_ref.strip())
            target_path = target_path.strip("/")
            if is_builtin_namespace_config_path(target_path):
                target_results.append(
                    {
                        "path": target_ref,
                        "status": "skipped",
                        "reason": "builtin_config",
                    }
                )
                continue

            target_tm = type(self)(self.namespace, target_path, auth=self.auth)
            try:
                target_item = target_tm.get_or_raise(["config"])
            except TreeItem.DoesNotExist:
                target_results.append(
                    {
                        "path": target_ref,
                        "status": "skipped",
                        "reason": "not_found",
                    }
                )
                continue

            try:
                LockManager.ensure_paths_writable(self.namespace, [target_path])
            except PathLocked as exc:
                target_results.append(
                    {
                        "path": target_ref,
                        "status": "skipped",
                        "reason": f"locked:{exc.lock_path}",
                    }
                )
                continue

            target_version = self.resolve_version(target_item, target_version_ref)
            target_metadata, _ = ConfigValidationManager.parse_config_yaml_document(target_version.data)
            target_versions.append(
                PropagationTargetVersion(
                    target_ref=target_ref,
                    target_path=target_path,
                    version_number=target_version.version,
                    version_data=target_version.data,
                    metadata=target_metadata,
                )
            )

        for outcome in PropagationManager.plan_propagation(
            source_metadata=source_metadata,
            source_body=source_body,
            rules=rules,
            targets=target_versions,
            source_yaml=source_version.data,
        ):
            if outcome["status"] != "updated":
                target_results.append(outcome)
                continue

            target_tm = type(self)(self.namespace, outcome["target_path"], auth=self.auth)
            try:
                with transaction.atomic():
                    target_tm.update_item(outcome["merged_yaml"])
            except PermissionDenied:
                target_results.append(
                    {
                        "path": outcome["path"],
                        "status": "skipped",
                        "reason": "permission_denied",
                    }
                )
                continue
            except Exception as exc:
                target_results.append(
                    {
                        "path": outcome["path"],
                        "status": "error",
                        "reason": str(exc),
                    }
                )
                continue

            target_item = target_tm.get_or_raise(["config"])
            target_item.refresh_from_db()
            target_results.append(
                {
                    "path": outcome["path"],
                    "status": "updated",
                    "version": target_item.tags.get("latest"),
                }
            )

        return self._finalize_propagate_config(
            source_version=source_version.version,
            trigger=trigger,
            trigger_tag=trigger_tag,
            target_results=target_results,
        )

    @staticmethod
    def _propagate_audit_payload(
        trigger: str,
        trigger_tag: str,
        targets: list[dict],
    ) -> str:
        data: dict = {"trigger": trigger}
        if trigger_tag:
            data["trigger_tag"] = trigger_tag
        updated = [
            {"path": t["path"], "version": t["version"]}
            for t in targets
            if t.get("status") == "updated" and t.get("version") is not None
        ]
        unchanged = [t["path"] for t in targets if t.get("status") == "unchanged" and t.get("path")]
        if updated:
            data["targets"] = updated
        if unchanged:
            data["unchanged"] = unchanged
        return json.dumps(data, separators=(",", ":"))

    def _finalize_propagate_config(
        self,
        *,
        source_version: int,
        trigger: str,
        trigger_tag: str,
        target_results: list[dict],
    ) -> dict:
        enrich_audit(
            object_version=source_version,
            subresource=self._propagate_audit_payload(trigger, trigger_tag, target_results),
        )
        return {
            "source_path": self.path,
            "source_version": source_version,
            "trigger": trigger,
            "targets": target_results,
        }

    @staticmethod
    def get_webhooks_config_version(namespace) -> Optional[tuple[str, int]]:
        """Return active (tag, version_number) for namespace ``_webhooks``, or None."""
        from . import TreeManager

        config_item = TreeManager(namespace, "_webhooks", auth=None).get_item("config")
        if config_item is None:
            return None
        tag = getattr(namespace, "webhooks_tag", None) or "latest"
        version_number = config_item.tags.get(tag)
        if version_number is None:
            return None
        return tag, version_number
