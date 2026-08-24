from ._common import *


class TreeDiffMixin:
    @staticmethod
    def format_subresource(types: list[str], values: list[str]) -> tuple[str, str]:
        """Join parallel non-version type/value lists into stored subresource fields."""
        if "version" in types:
            raise ValueError("version must use object_version, not subresource")
        if len(types) != len(values):
            raise ValueError("subresource types and values must have the same length")
        if not types:
            return "", ""
        return ",".join(types), ",".join(str(v) for v in values)

    @staticmethod
    def _diff_subresource_fields(
        from_ref: str,
        to_ref: str,
        to_path: str | None,
    ) -> tuple[str | None, str | None]:
        """Build audit ``subresource_type`` / ``subresource`` for a config diff.

        Tag names are taken from ``from_ref`` and ``to_ref`` when those refs are
        tags (not numeric versions). When ``to_path`` is set, the destination
        path is included for cross-path diffs.
        """
        types: list[str] = []
        values: list[str] = []
        for key, ref in (("from", from_ref), ("to", to_ref)):
            tag_sr = tag_subresource_from_ref(str(ref))
            if tag_sr:
                types.append(key)
                values.append(tag_sr[1])
        if to_path:
            types.append("path")
            values.append(to_path.strip("/"))
        if not types:
            return None, None
        return TreeDiffMixin.format_subresource(types, values)

    def _resolve_diff_items(
        self,
        to_path: Optional[str] = None,
    ) -> tuple[Any, Any, Optional[str]]:
        """Resolve source and destination items for a diff operation."""
        from_item = self.get_or_raise()
        if to_path is not None:
            to_path = to_path.strip("/")
            if not to_path:
                raise ValidationError("to_path must not be empty")
            to_item = type(self)(self.namespace, to_path, auth=None).get_or_raise()
        else:
            to_item = from_item

        if from_item.node_type != to_item.node_type:
            raise ValidationError(f"Cannot diff {from_item.node_type!r} with {to_item.node_type!r}")
        return from_item, to_item, to_path

    def _build_diff_result(
        self,
        *,
        from_item,
        to_item,
        to_path: Optional[str],
        from_ref: str,
        to_ref: str,
        reveal: bool,
    ) -> dict:
        sr_type, sr_value = self._diff_subresource_fields(from_ref, to_ref, to_path)
        enrich_audit(subresource_type=sr_type, subresource=sr_value)

        from_side = self._load_diff_side(from_item, from_ref, reveal)
        to_side = self._load_diff_side(to_item, to_ref, reveal)

        decryption_required = from_item.node_type == "secret" and not reveal
        identical = None
        if not decryption_required:
            identical = from_side["data"] == to_side["data"]

        return {
            "path": self.path,
            "to_path": to_path,
            "from_side": from_side,
            "to_side": to_side,
            "identical": identical,
            "decryption_required": decryption_required,
        }

    def diff_item(
        self,
        from_ref: str = "latest",
        to_ref: str = "latest",
        *,
        to_path: Optional[str] = None,
        reveal: bool = False,
    ) -> dict:
        """Compare two versions of one item or two items at different paths."""
        if self.item_type == "folder":
            raise ValidationError("Diff is not supported for folders")

        node_type = self.get_or_raise().node_type
        handlers = {
            "config": self.diff_configs,
            "template": self.diff_templates,
            "secret": self.diff_secrets,
            "resolver": self._diff_resolver,
        }
        if node_type not in handlers:
            raise ValidationError(f"Diff is not supported for node type {node_type!r}") from None

        return handlers[node_type](
            from_ref=from_ref,
            to_ref=to_ref,
            to_path=to_path,
            reveal=reveal,
        )

    @audit("config", operation=OP_DIFF_ITEM)
    @require_permissions(
        PermCheck("config:read"),
        PermCheck(
            action=lambda self, to_path=None: "config:read" if to_path else None,
            resource=arg("to_path", lambda p: p.strip("/") if p else ""),
        ),
    )
    def diff_configs(
        self,
        from_ref: str = "latest",
        to_ref: str = "latest",
        *,
        to_path: Optional[str] = None,
        reveal: bool = False,
    ) -> dict:
        """Compare two config versions or two configs at different paths."""
        self.get_or_raise(["config"])
        from_item, to_item, to_path = self._resolve_diff_items(to_path)
        return self._build_diff_result(
            from_item=from_item,
            to_item=to_item,
            to_path=to_path,
            from_ref=from_ref,
            to_ref=to_ref,
            reveal=reveal,
        )

    @audit("template", operation=OP_DIFF_ITEM)
    @require_permissions(
        PermCheck("template:read"),
        PermCheck(
            action=lambda self, to_path=None: "template:read" if to_path else None,
            resource=arg("to_path", lambda p: p.strip("/") if p else ""),
        ),
    )
    def diff_templates(
        self,
        from_ref: str = "latest",
        to_ref: str = "latest",
        *,
        to_path: Optional[str] = None,
        reveal: bool = False,
    ) -> dict:
        """Compare two template versions or two templates at different paths."""
        self.get_or_raise(["template"])
        from_item, to_item, to_path = self._resolve_diff_items(to_path)
        return self._build_diff_result(
            from_item=from_item,
            to_item=to_item,
            to_path=to_path,
            from_ref=from_ref,
            to_ref=to_ref,
            reveal=reveal,
        )

    @audit("secret", operation=OP_DIFF_ITEM)
    @require_permissions(
        PermCheck("secret:read"),
        PermCheck(
            action=lambda self, to_path=None: "secret:read" if to_path else None,
            resource=arg("to_path", lambda p: p.strip("/") if p else ""),
        ),
    )
    def diff_secrets(
        self,
        from_ref: str = "latest",
        to_ref: str = "latest",
        *,
        to_path: Optional[str] = None,
        reveal: bool = False,
    ) -> dict:
        """Compare two secret versions or two secrets at different paths."""
        self.get_or_raise(["secret"])
        from_item, to_item, to_path = self._resolve_diff_items(to_path)
        return self._build_diff_result(
            from_item=from_item,
            to_item=to_item,
            to_path=to_path,
            from_ref=from_ref,
            to_ref=to_ref,
            reveal=reveal,
        )

    @audit("resolver", operation=OP_DIFF_ITEM)
    @require_permissions(
        PermCheck("resolver:read"),
        PermCheck(
            action=lambda self, to_path=None: "resolver:read" if to_path else None,
            resource=arg("to_path", lambda p: p.strip("/") if p else ""),
        ),
    )
    def _diff_resolver(
        self,
        from_ref: str = "latest",
        to_ref: str = "latest",
        *,
        to_path: Optional[str] = None,
        reveal: bool = False,
    ) -> dict:
        """Compare two resolver configurations at the same or different paths."""
        self.get_or_raise(["resolver"])
        from_item, to_item, to_path = self._resolve_diff_items(to_path)
        return self._build_diff_result(
            from_item=from_item,
            to_item=to_item,
            to_path=to_path,
            from_ref=from_ref,
            to_ref=to_ref,
            reveal=reveal,
        )

    def _load_diff_side(self, item, version_ref: str, reveal: bool) -> dict:
        """Build one diff side dict for config, template, secret, or resolver."""
        if item.node_type in ("config", "template"):
            version_obj = self.resolve_version(item, version_ref)
            return {
                "path": item.path,
                "node_type": item.node_type,
                "requested": version_ref,
                "version": version_obj.version,
                "data": version_obj.data,
            }

        if item.node_type == "secret":
            version_obj = self.resolve_version(item, version_ref)
            side = {
                "path": item.path,
                "node_type": "secret",
                "requested": version_ref,
                "version": version_obj.version,
            }
            if reveal:
                crypto = CryptoManager(self.namespace)
                side["data"] = crypto.decrypt_secret(version_obj.encrypted_data)
            return side

        if item.node_type == "resolver":
            configuration = item.configuration
            if isinstance(configuration, str):
                data = configuration
            else:
                data = json.dumps(configuration, sort_keys=True, separators=(",", ":"))
            return {
                "path": item.path,
                "node_type": "resolver",
                "requested": version_ref,
                "version": 1,
                "data": data,
            }

        raise ValidationError(f"Diff is not supported for node type {item.node_type!r}")
