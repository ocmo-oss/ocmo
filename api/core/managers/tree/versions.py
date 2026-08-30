from ._common import *


class TreeVersionsMixin:
    def _generic_list_versions(
        self, *, limit: int = 100, offset: int = 0, q: str | None = None, tagged_only: bool = False
    ) -> dict:
        item = self.item
        tags_per_version: dict[int, list[str]] = {}
        for tag, ver in item.tags.items():
            tags_per_version.setdefault(ver, []).append(tag)

        ordered_versions = list(item.versions.order_by("-version"))
        if tagged_only:
            ordered_versions = [
                version_obj for version_obj in ordered_versions if tags_per_version.get(version_obj.version)
            ]
        q_normalized = (q or "").strip().lower()
        if q_normalized:
            ordered_versions = [
                version_obj
                for version_obj in ordered_versions
                if (
                    q_normalized in str(version_obj.version)
                    or q_normalized in (version_obj.updater or "").lower()
                    or any(
                        q_normalized in tag_name.lower() for tag_name in tags_per_version.get(version_obj.version, [])
                    )
                )
            ]

        versions_count = len(ordered_versions)
        version_rows = []
        for version_obj in ordered_versions[offset : offset + limit]:
            version_rows.append(
                {
                    "version": version_obj.version,
                    "tags": tags_per_version.get(version_obj.version, []),
                    "updater": version_obj.updater,
                    "updated_at": version_obj.updated_at,
                    "deleted_at": version_obj.deleted_at,
                }
            )

        return {"item": item, "versions": version_rows, "versions_count": versions_count}

    def list_versions(self, *, limit=100, offset=0, q: str | None = None, tagged_only: bool = False) -> dict:
        """Return versions (metadata only) for a config, template, or secret."""
        handlers = {
            "config": self.list_config_versions,
            "template": self.list_template_versions,
            "secret": self.list_secret_versions,
        }
        node_type = self.get_or_raise().node_type
        if node_type not in handlers:
            raise ValidationError(f"Version history is not supported for {node_type!r} items")
        return handlers[node_type](limit=limit, offset=offset, q=q, tagged_only=tagged_only)

    @audit("config", operation=OP_LIST_VERSIONS)
    @require_permissions(PermCheck("config:read"))
    def list_config_versions(
        self, *, limit: int = 100, offset: int = 0, q: str | None = None, tagged_only: bool = False
    ) -> dict:
        self.get_or_raise(["config"])
        return self._generic_list_versions(limit=limit, offset=offset, q=q, tagged_only=tagged_only)

    @audit("template", operation=OP_LIST_VERSIONS)
    @require_permissions(PermCheck("template:read"))
    def list_template_versions(
        self, *, limit: int = 100, offset: int = 0, q: str | None = None, tagged_only: bool = False
    ) -> dict:
        self.get_or_raise(["template"])
        return self._generic_list_versions(limit=limit, offset=offset, q=q, tagged_only=tagged_only)

    @audit("secret", operation=OP_LIST_VERSIONS)
    @require_permissions(PermCheck("secret:read"))
    def list_secret_versions(
        self, *, limit: int = 100, offset: int = 0, q: str | None = None, tagged_only: bool = False
    ) -> dict:
        self.get_or_raise(["secret"])
        return self._generic_list_versions(limit=limit, offset=offset, q=q, tagged_only=tagged_only)
