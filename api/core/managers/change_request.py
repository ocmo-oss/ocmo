"""Change request lifecycle for config, template, and secret tree items."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from ..constants.audit_operations import (
    OP_APPLY_CHANGE_REQUEST,
    OP_APPROVE_CHANGE_REQUEST,
    OP_COMMENT_CHANGE_REQUEST,
    OP_CREATE_CHANGE_REQUEST,
    OP_DELETE_CHANGE_REQUEST_COMMENT,
    OP_LIST_CHANGE_REQUESTS,
    OP_READ_CHANGE_REQUEST,
    OP_REJECT_CHANGE_REQUEST,
    OP_UNAPPROVE_CHANGE_REQUEST,
    OP_UPDATE_CHANGE_REQUEST,
    OP_UPDATE_CHANGE_REQUEST_COMMENT,
    OP_WITHDRAW_CHANGE_REQUEST,
)
from ..decorators import PermCheck, audit, enrich_audit, require_permissions, webhook
from ..exceptions import (
    ChangeRequestConflict,
    ChangeRequestNotApplicable,
    ChangeRequestNotFound,
    NotFound,
    PermissionDenied,
    VersionNotFound,
)
from ..models import ChangeRequest, ChangeRequestApproval, ChangeRequestComment, Namespace, TreeItem
from ..shortcuts import (
    change_request_number_from_ref,
    is_change_request_ref,
    validate_path_characters,
)
from ..utils.change_request_content import (
    change_request_cache_stamp,
    is_substantive_content_change,
    rewrite_cr_refs_in_body,
)
from .auth import AuthManager
from .crypto import CryptoManager
from .lock import LockManager
from .tree import TreeManager
from .tree.config_ops import collect_ocmo_reference_paths
from .tree_capabilities import is_builtin_namespace_path
from .webhook import WebhookManager

_VERSIONED_TYPES = frozenset({"config", "template", "secret"})


def _cr_webhook_version(_self: Any, result: dict[str, Any], bound: dict[str, Any]) -> int:
    if "number" in result:
        return int(result["number"])
    return int(bound["number"])


@dataclass
class _CrVersionView:
    """Stand-in for ConfigVersion/TemplateVersion/SecretVersion when reading ``@~N``."""

    version: int
    data: str | None = None
    encrypted_data: bytes | None = None
    deleted_at: datetime | None = None


class ChangeRequestManager:
    def __init__(self, namespace: Namespace, path: str, *, auth):
        self.namespace = namespace
        self.path = path.strip("/")
        validate_path_characters(self.path)
        self.auth = auth
        self._item: TreeItem | None = None

    def _webhook_cr_details(self, result: dict[str, Any], bound: dict[str, Any], **extra: Any) -> dict[str, Any]:
        item = self._item_or_raise()
        number = int(result["number"]) if "number" in result else int(bound["number"])
        status = result.get("status")
        base_version = result.get("base_version")
        title = result.get("title")
        if status is None:
            cr = ChangeRequest.objects.filter(tree_item=item, number=number).first()
            if cr is not None:
                status = cr.status
                base_version = cr.base_version
                title = cr.title
        details: dict[str, Any] = {
            "node_type": item.node_type,
            "number": number,
            "status": status,
            "base_version": base_version,
            "title": title,
        }
        details.update(extra)
        return details

    @classmethod
    def _dispatch_cr_webhook(
        cls,
        namespace: Namespace,
        *,
        path: str,
        number: int,
        event: str,
        details: dict[str, Any],
        auth=None,
    ) -> None:
        mgr = WebhookManager(namespace, auth=auth)
        mgr.dispatch(
            mgr.build_event(
                event,
                path=path.strip("/"),
                version=number,
                details=details,
            ),
        )

    def _feature_enabled(self) -> bool:
        return bool(self.namespace.change_requests_enabled)

    def _require_feature(self) -> None:
        if not self._feature_enabled():
            raise ChangeRequestNotFound("Change requests are not enabled for this namespace")

    def _item_or_raise(self) -> TreeItem:
        if self._item is not None:
            return self._item
        tm = TreeManager(self.namespace, self.path, auth=None)
        try:
            item = tm.get_or_raise(list(_VERSIONED_TYPES))
        except (TreeItem.DoesNotExist, NotFound):
            raise ChangeRequestNotFound(f"Item {self.path!r} not found")
        if item.node_type not in _VERSIONED_TYPES:
            raise ChangeRequestNotFound(f"Change requests are not supported for {item.node_type!r}")
        self._item = item
        return item

    def _typed_item_for_cr(self, cr: ChangeRequest) -> TreeItem:
        """Return config/template/secret instance so version relations (e.g. ``versions``) work."""
        raw = cr.tree_item
        path = raw.path.strip("/")
        if self._item is not None and self.path == path:
            return self._item
        tm = TreeManager(self.namespace, path, auth=None)
        return tm.get_or_raise([raw.node_type])

    def _read_perm(self, node_type: str) -> str:
        return f"{node_type}:read"

    def _write_perm(self, node_type: str) -> str:
        return f"{node_type}:write"

    def _permissions(self):
        return self.auth.permissions(self.namespace)

    def _ensure_read(self, item: TreeItem) -> None:
        self._permissions().require_tree(self._read_perm(item.node_type), self.path)

    def _ensure_write(self, item: TreeItem) -> None:
        self._permissions().require_tree(self._write_perm(item.node_type), self.path)

    @staticmethod
    def _latest_version_number(item: TreeItem) -> int:
        tags = getattr(item, "tags", None) or {}
        return int(tags.get("latest", 0))

    def _resolve_base_version(self, item: TreeItem, base_version_ref: str | None) -> int:
        tm = TreeManager(self.namespace, self.path, auth=None)
        ref = base_version_ref or "latest"
        if is_change_request_ref(ref):
            raise ChangeRequestConflict("base_version cannot be a change request reference")
        try:
            return tm.resolve_version(item, ref).version
        except VersionNotFound as exc:
            raise ChangeRequestConflict(str(exc)) from exc

    def _plaintext_at_version(self, item: TreeItem, version: int) -> str:
        tm = TreeManager(self.namespace, item.path, auth=None)
        reveal = item.node_type == "secret"
        side = tm._load_diff_side(item, str(version), reveal)
        return side.get("data") or ""

    def _reject_if_matches_base(self, item: TreeItem, base_version: int, body: str) -> None:
        if body == self._plaintext_at_version(item, base_version):
            raise ChangeRequestConflict("Change request content must differ from the base version")

    def _plaintext_content(self, cr: ChangeRequest) -> str:
        item = cr.tree_item
        if item.node_type == "secret":
            if not cr.content_encrypted:
                return ""
            return CryptoManager(self.namespace).decrypt_secret(cr.content_encrypted) or ""
        return cr.content

    def _store_content(self, item: TreeItem, plaintext: str, cr: ChangeRequest) -> None:
        if item.node_type == "secret":
            cr.content = ""
            cr.content_encrypted = CryptoManager(self.namespace).encrypt_secret(plaintext)
        else:
            cr.content = plaintext
            cr.content_encrypted = None

    def get_cr_version_view(self, item: TreeItem, version_ref: str) -> _CrVersionView:
        self._require_feature()
        number = change_request_number_from_ref(version_ref)
        cr = ChangeRequest.objects.filter(
            tree_item_id=item.pk,
            number=number,
        ).first()
        if cr is None:
            raise VersionNotFound(f"Change request ~{number} not found on {item.path}")
        if item.node_type == "secret":
            raw_enc = cr.content_encrypted
            enc: bytes | None = None
            if raw_enc is not None:
                enc = raw_enc if isinstance(raw_enc, bytes) else bytes(raw_enc)
            return _CrVersionView(version=number, encrypted_data=enc)
        return _CrVersionView(version=number, data=self._plaintext_content(cr))

    @classmethod
    def cache_stamp_for(cls, item: TreeItem, version_ref: str) -> str | None:
        """Return a resolve-cache stamp for ``path@~N``, or None when not a live CR ref."""
        if not is_change_request_ref(version_ref):
            return None
        number = change_request_number_from_ref(version_ref)
        cr = ChangeRequest.objects.filter(tree_item_id=item.pk, number=number).first()
        if cr is None:
            return None
        mgr = cls(item.namespace, item.path.strip("/"), auth=None)
        plaintext = mgr._plaintext_content(cr)
        return change_request_cache_stamp(cr.updated_at, plaintext)

    @classmethod
    def on_version_created(cls, namespace: Namespace, item: TreeItem) -> None:
        if not namespace.change_requests_auto_reject_on_new_version:
            return
        open_crs = list(
            ChangeRequest.objects.filter(
                tree_item=item,
                status=ChangeRequest.STATUS_OPEN,
            ),
        )
        if not open_crs:
            return
        now = timezone.now()
        ChangeRequest.objects.filter(
            tree_item=item,
            status=ChangeRequest.STATUS_OPEN,
        ).update(
            status=ChangeRequest.STATUS_REJECTED,
            rejected_reason="new_version_published",
            rejected_by="system",
            rejected_at=now,
        )
        path = item.path.strip("/")
        for cr in open_crs:
            cls._dispatch_cr_webhook(
                namespace,
                path=path,
                number=cr.number,
                event="change_request.rejected",
                details={
                    "node_type": item.node_type,
                    "number": cr.number,
                    "status": ChangeRequest.STATUS_REJECTED,
                    "base_version": cr.base_version,
                    "title": cr.title,
                    "reject_kind": "system",
                    "rejected_reason": "new_version_published",
                    "rejected_by": "system",
                },
                auth=None,
            )

    @classmethod
    def rewrite_peer_refs_on_apply(
        cls,
        namespace: Namespace,
        applied_item: TreeItem,
        applied_cr_number: int,
        applied_version: int,
    ) -> list[int]:
        """Rewrite ``path@~N`` → ``path@V`` in open CRs; return affected CR numbers."""
        path = applied_item.path.strip("/")
        affected: list[int] = []
        open_crs = ChangeRequest.objects.filter(
            tree_item__namespace=namespace,
            status=ChangeRequest.STATUS_OPEN,
        ).select_related("tree_item")
        mgr = cls(namespace, path, auth=None)
        for cr in open_crs:
            peer_item = cr.tree_item
            body = mgr._plaintext_content(cr)
            new_body = rewrite_cr_refs_in_body(
                body,
                node_type=peer_item.node_type,
                item_path=peer_item.path,
                target_resolved_path=path,
                cr_number=applied_cr_number,
                applied_version=applied_version,
            )
            if new_body == body:
                continue
            peer_mgr = cls(namespace, peer_item.path, auth=None)
            peer_mgr._store_content(peer_item, new_body, cr)
            cr.save(update_fields=["content", "content_encrypted", "updated_at"])
            affected.append(cr.number)
        return affected

    def _validate_cr_body(
        self,
        item: TreeItem,
        body: str,
        *,
        allow_cr_refs: bool,
        strict: bool = True,
    ) -> None:
        if is_builtin_namespace_path(self.path):
            raise ChangeRequestConflict("Change requests are not allowed on built-in namespace paths")
        tm = TreeManager(self.namespace, self.path, auth=self.auth)
        if item.node_type == "config":
            if strict:
                tm._validate_config_on_save(
                    body,
                    validate_references=True,
                    allow_cr_refs=allow_cr_refs,
                )
            else:
                from .config_validation import ConfigValidationManager

                ConfigValidationManager(config_path=self.path, data_yaml=body).parse()
        elif item.node_type == "template":
            from ..shortcuts import make_template_environment

            make_template_environment().parse(body)
        elif item.node_type == "secret":
            SecretManager = __import__("core.managers.secret", fromlist=["SecretManager"]).SecretManager
            SecretManager(self.namespace, self.path, secret_obj=item, auth=self.auth)._validate_yaml(body)

        if allow_cr_refs:
            self._validate_cr_metadata_refs(item, body)

    def _config_metadata_from_body(self, body: str):
        from .config_validation import ConfigValidationManager

        validator = ConfigValidationManager(config_path=self.path, data_yaml=body)
        validator.parse()
        return validator.metadata

    def _validate_cr_metadata_refs(self, item: TreeItem, body: str) -> None:
        if item.node_type != "config":
            return
        metadata = self._config_metadata_from_body(body)
        if not metadata.model_dump(exclude_none=True):
            return
        base_folder = "/".join(self.path.split("/")[:-1])
        refs = collect_ocmo_reference_paths(metadata, base_folder=base_folder)
        effective = self.path.strip("/")
        for _nt, resolved, version_ref in refs:
            if is_change_request_ref(version_ref):
                if resolved.strip("/") == effective:
                    raise ChangeRequestConflict("Change request cannot reference a change request on the same resource")
                number = change_request_number_from_ref(version_ref)
                target = TreeManager(self.namespace, resolved, auth=None).get_item()
                if target is None:
                    raise DjangoValidationError(f"Config {resolved!r} not found")
                peer = ChangeRequest.objects.filter(
                    tree_item_id=target.pk,
                    number=number,
                    status=ChangeRequest.STATUS_OPEN,
                ).first()
                if peer is None:
                    raise ChangeRequestConflict(
                        f"Open change request ~{number} not found on {resolved!r}",
                    )

    def body_has_cr_refs(self, item: TreeItem, body: str) -> bool:
        if item.node_type != "config":
            return False
        metadata = self._config_metadata_from_body(body)
        if not metadata.model_dump(exclude_none=True):
            return False
        base_folder = "/".join(self.path.split("/")[:-1])
        refs = collect_ocmo_reference_paths(metadata, base_folder=base_folder)
        return any(is_change_request_ref(v) for _t, _p, v in refs)

    def _collect_issues(self, cr: ChangeRequest, item: TreeItem) -> list[str]:
        if cr.status != ChangeRequest.STATUS_OPEN:
            return []
        issues: list[str] = []
        body = self._plaintext_content(cr)
        try:
            self._validate_cr_body(item, body, allow_cr_refs=True)
        except DjangoValidationError as exc:
            if hasattr(exc, "messages"):
                issues.extend(str(m) for m in exc.messages)
            else:
                issues.append(str(exc))
        except ChangeRequestConflict as exc:
            issues.append(str(exc))
        except Exception as exc:
            issues.append(str(exc))

        if self.body_has_cr_refs(item, body):
            msg = "References another change request; apply is blocked until resolved."
            if msg not in issues and not any("change request" in i.lower() for i in issues):
                issues.append(msg)

        required = self.namespace.change_requests_required_approvals
        approval_count = cr.approvals.count()
        if approval_count < required:
            issues.append(
                f"Insufficient approvals ({approval_count} of {required} required).",
            )

        latest = self._latest_version_number(item)
        if latest > cr.base_version:
            issues.append(
                "Base version is no longer latest; compare Latest → CR before applying.",
            )

        last_ver = item.versions.order_by("-version").first()
        if item.node_type == "secret" and last_ver and last_ver.encrypted_data:
            existing = CryptoManager(self.namespace).decrypt_secret(last_ver.encrypted_data)
            if existing == body:
                issues.append("Content is identical to the latest published version.")
        elif last_ver and getattr(last_ver, "data", None) == body:
            issues.append("Content is identical to the latest published version.")

        return issues

    def _serialize_flags(self, cr: ChangeRequest, item: TreeItem) -> dict[str, Any]:
        latest = self._latest_version_number(item)
        approval_count = cr.approvals.count()
        required = self.namespace.change_requests_required_approvals
        actor = AuthManager.resolve_actor_identity(self.auth)
        body = self._plaintext_content(cr)
        has_cr_refs = self.body_has_cr_refs(item, body) if cr.status == ChangeRequest.STATUS_OPEN else False
        identical_to_latest = any(
            issue == "Content is identical to the latest published version." for issue in self._collect_issues(cr, item)
        )
        can_apply = (
            cr.status == ChangeRequest.STATUS_OPEN
            and approval_count >= required
            and not has_cr_refs
            and not identical_to_latest
            and bool(body.strip())
            and self._permissions().check_tree(self._write_perm(item.node_type), self.path)
        )
        already_approved = cr.approvals.filter(approver=actor).exists()
        can_approve = (
            cr.status == ChangeRequest.STATUS_OPEN
            and cr.created_by != actor
            and not already_approved
            and self._permissions().check_tree(self._write_perm(item.node_type), self.path)
        )
        can_unapprove = cr.status == ChangeRequest.STATUS_OPEN and already_approved
        projected = latest + 1 if latest else 1
        return {
            "base_superseded": latest > cr.base_version,
            "latest_version": latest,
            "approval_count": approval_count,
            "required_approvals": required,
            "can_apply": can_apply,
            "can_approve": can_approve,
            "can_unapprove": can_unapprove,
            "projected_version_on_apply": projected,
            "has_cr_references": has_cr_refs,
        }

    def _depends_on(self, item: TreeItem, body: str) -> list[dict[str, Any]]:
        if item.node_type != "config":
            return []
        metadata = self._config_metadata_from_body(body)
        if not metadata.model_dump(exclude_none=True):
            return []
        base_folder = "/".join(self.path.split("/")[:-1])
        refs = collect_ocmo_reference_paths(metadata, base_folder=base_folder)
        deps: list[dict[str, Any]] = []
        seen: set[tuple[str, int]] = set()
        for node_type, resolved, version_ref in refs:
            if not is_change_request_ref(version_ref):
                continue
            path = resolved.strip("/")
            number = change_request_number_from_ref(version_ref)
            key = (path, number)
            if key in seen:
                continue
            seen.add(key)
            deps.append(
                {
                    "path": path,
                    "node_type": node_type,
                    "number": number,
                },
            )
        deps.sort(key=lambda r: (r["path"], r["number"]))
        return deps

    def _referenced_by(self, cr: ChangeRequest, item: TreeItem) -> list[dict[str, Any]]:
        target_path = item.path.strip("/")
        target_number = cr.number
        peers = (
            ChangeRequest.objects.filter(
                tree_item__namespace=self.namespace,
                status=ChangeRequest.STATUS_OPEN,
            )
            .exclude(pk=cr.pk)
            .select_related("tree_item")
        )
        referrers: list[dict[str, Any]] = []
        for peer in peers:
            peer_item = peer.tree_item
            if peer_item.node_type != "config":
                continue
            body = self._plaintext_content(peer)
            metadata = self._config_metadata_from_body(body)
            if not metadata.model_dump(exclude_none=True):
                continue
            base_folder = "/".join(peer_item.path.split("/")[:-1])
            refs = collect_ocmo_reference_paths(metadata, base_folder=base_folder)
            for _nt, resolved, version_ref in refs:
                if not is_change_request_ref(version_ref):
                    continue
                if resolved.strip("/") != target_path:
                    continue
                if change_request_number_from_ref(version_ref) != target_number:
                    continue
                referrers.append(
                    {
                        "path": peer_item.path,
                        "node_type": peer_item.node_type,
                        "number": peer.number,
                    },
                )
                break
        referrers.sort(key=lambda r: (r["path"], r["number"]))
        return referrers

    def _to_dict(self, cr: ChangeRequest, *, include_content: bool = False) -> dict[str, Any]:
        item = self._typed_item_for_cr(cr)
        data = {
            "path": item.path,
            "node_type": item.node_type,
            "number": cr.number,
            "status": cr.status,
            "base_version": cr.base_version,
            "title": cr.title,
            "description": cr.description,
            "created_by": cr.created_by,
            "created_at": cr.created_at,
            "updated_at": cr.updated_at,
            "applied_version": cr.applied_version,
            "applied_by": cr.applied_by,
            "applied_at": cr.applied_at,
            "rejected_reason": cr.rejected_reason,
            "rejected_by": cr.rejected_by,
            "rejected_at": cr.rejected_at,
            "approvers": list(cr.approvals.order_by("created_at").values_list("approver", flat=True)),
            "approval_events": [
                {"approver": a.approver, "created_at": a.created_at} for a in cr.approvals.order_by("created_at")
            ],
            **self._serialize_flags(cr, item),
            "referenced_by": self._referenced_by(cr, item),
            "depends_on": self._depends_on(item, self._plaintext_content(cr)),
            "issues": self._collect_issues(cr, item),
        }
        if include_content:
            data["content"] = self._plaintext_content(cr)
        return data

    @audit("change_request", operation=OP_LIST_CHANGE_REQUESTS)
    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:read"))
    def list_requests(
        self,
        *,
        status: str | None = None,
        created_by: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        self._require_feature()
        item = self._item_or_raise()
        self._ensure_read(item)
        qs = ChangeRequest.objects.filter(tree_item=item).order_by("-number")
        if status:
            qs = qs.filter(status=status)
        if created_by:
            qs = qs.filter(created_by=created_by)
        total = qs.count()
        rows = [self._to_dict(cr) for cr in qs[offset : offset + limit]]
        return {"items": rows, "total": total, "limit": limit, "offset": offset}

    @audit("change_request", operation=OP_READ_CHANGE_REQUEST)
    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:read"))
    def get_request(self, number: int, *, include_content: bool = False) -> dict[str, Any]:
        self._require_feature()
        item = self._item_or_raise()
        self._ensure_read(item)
        cr = ChangeRequest.objects.filter(tree_item=item, number=number).first()
        if cr is None:
            raise ChangeRequestNotFound(f"Change request ~{number} not found")
        enrich_audit(object_version=number)
        return self._to_dict(cr, include_content=include_content)

    @webhook(
        "change_request.created",
        version=_cr_webhook_version,
        details=lambda self, result, bound: self._webhook_cr_details(result, bound),
    )
    @audit("change_request", operation=OP_CREATE_CHANGE_REQUEST)
    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:read"))
    def create(
        self,
        body: str,
        *,
        title: str = "",
        description: str = "",
        base_version_ref: str | None = None,
    ) -> dict[str, Any]:
        self._require_feature()
        item = self._item_or_raise()
        self._ensure_read(item)
        if is_builtin_namespace_path(self.path):
            raise ChangeRequestConflict("Change requests are not allowed on built-in namespace paths")
        actor = AuthManager.resolve_actor_identity(self.auth)
        open_count = ChangeRequest.objects.filter(
            tree_item=item,
            created_by=actor,
            status=ChangeRequest.STATUS_OPEN,
        ).count()
        max_open = self.namespace.change_requests_max_open_per_user_per_resource
        if open_count >= max_open:
            raise ChangeRequestConflict(
                f"Maximum open change requests per user on this resource is {max_open}",
            )
        base_version = self._resolve_base_version(item, base_version_ref)
        self._validate_cr_body(item, body, allow_cr_refs=True, strict=False)
        self._reject_if_matches_base(item, base_version, body)
        title = title.strip()
        if not title:
            raise ChangeRequestConflict("Title is required")
        description = description.strip()
        with transaction.atomic():
            cr = ChangeRequest(
                tree_item=item,
                base_version=base_version,
                title=title[:200],
                description=description[:4096],
                created_by=actor,
                status=ChangeRequest.STATUS_OPEN,
            )
            self._store_content(item, body, cr)
            cr.save()
            desc = description.strip()
            if desc:
                ChangeRequestComment.objects.create(
                    change_request=cr,
                    author=actor,
                    body=desc[:8192],
                )
        enrich_audit(object_version=cr.number)
        return self._to_dict(cr, include_content=True)

    @webhook(
        "change_request.updated",
        version=_cr_webhook_version,
        details=lambda self, result, bound: self._webhook_cr_details(
            result,
            bound,
            update_kind="content",
        ),
    )
    @audit("change_request", operation=OP_UPDATE_CHANGE_REQUEST)
    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:read"))
    def update(self, number: int, body: str) -> dict[str, Any]:
        self._require_feature()
        item = self._item_or_raise()
        cr = ChangeRequest.objects.filter(tree_item=item, number=number).first()
        if cr is None:
            raise ChangeRequestNotFound(f"Change request ~{number} not found")
        if cr.status != ChangeRequest.STATUS_OPEN:
            raise ChangeRequestNotApplicable("Only open change requests can be updated")
        if cr.created_by != AuthManager.resolve_actor_identity(self.auth):
            raise ChangeRequestNotApplicable("Only the author can update this change request")
        old_body = self._plaintext_content(cr)
        typed = self._typed_item_for_cr(cr)
        self._validate_cr_body(item, body, allow_cr_refs=True, strict=False)
        self._reject_if_matches_base(typed, cr.base_version, body)
        with transaction.atomic():
            if self.namespace.change_requests_reset_approvals_on_change and is_substantive_content_change(
                old_body, body
            ):
                cr.approvals.all().delete()
            self._store_content(item, body, cr)
            cr.save()
        enrich_audit(object_version=number)
        return self._to_dict(cr, include_content=True)

    @webhook(
        "change_request.updated",
        version=_cr_webhook_version,
        details=lambda self, result, bound: self._webhook_cr_details(
            result,
            bound,
            update_kind="metadata",
        ),
    )
    @audit("change_request", operation=OP_UPDATE_CHANGE_REQUEST)
    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:read"))
    def patch_metadata(
        self,
        number: int,
        *,
        title: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        self._require_feature()
        if title is None and description is None:
            raise ChangeRequestConflict("No metadata fields to update")
        item = self._item_or_raise()
        cr = ChangeRequest.objects.filter(tree_item=item, number=number).first()
        if cr is None:
            raise ChangeRequestNotFound(f"Change request ~{number} not found")
        if cr.status != ChangeRequest.STATUS_OPEN:
            raise ChangeRequestNotApplicable("Only open change requests can be updated")
        if cr.created_by != AuthManager.resolve_actor_identity(self.auth):
            raise ChangeRequestNotApplicable("Only the author can update this change request")
        if title is not None:
            cr.title = title[:200]
        if description is not None:
            cr.description = description[:4096]
        cr.save()
        enrich_audit(object_version=number)
        return self._to_dict(cr, include_content=False)

    @webhook(
        "change_request.approved",
        version=_cr_webhook_version,
        details=lambda self, result, bound: self._webhook_cr_details(
            result,
            bound,
            approval_count=len(result.get("approvers") or []),
            required_approvals=self.namespace.change_requests_required_approvals,
        ),
    )
    @audit("change_request", operation=OP_APPROVE_CHANGE_REQUEST)
    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:write"))
    def approve(self, number: int) -> dict[str, Any]:
        self._require_feature()
        item = self._item_or_raise()
        self._ensure_write(item)
        cr = ChangeRequest.objects.filter(tree_item=item, number=number).first()
        if cr is None:
            raise ChangeRequestNotFound(f"Change request ~{number} not found")
        if cr.status != ChangeRequest.STATUS_OPEN:
            raise ChangeRequestNotApplicable("Only open change requests can be approved")
        actor = AuthManager.resolve_actor_identity(self.auth)
        if cr.created_by == actor:
            raise ChangeRequestNotApplicable("Author cannot approve their own change request")
        ChangeRequestApproval.objects.get_or_create(change_request=cr, approver=actor)
        enrich_audit(object_version=number)
        return self._to_dict(cr)

    @webhook(
        "change_request.unapproved",
        version=_cr_webhook_version,
        details=lambda self, result, bound: self._webhook_cr_details(
            result,
            bound,
            approval_count=len(result.get("approvers") or []),
            required_approvals=self.namespace.change_requests_required_approvals,
        ),
    )
    @audit("change_request", operation=OP_UNAPPROVE_CHANGE_REQUEST)
    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:write"))
    def unapprove(self, number: int) -> dict[str, Any]:
        self._require_feature()
        item = self._item_or_raise()
        self._ensure_write(item)
        cr = ChangeRequest.objects.filter(tree_item=item, number=number).first()
        if cr is None:
            raise ChangeRequestNotFound(f"Change request ~{number} not found")
        if cr.status != ChangeRequest.STATUS_OPEN:
            raise ChangeRequestNotApplicable("Only open change requests can be unapproved")
        actor = AuthManager.resolve_actor_identity(self.auth)
        deleted, _ = ChangeRequestApproval.objects.filter(
            change_request=cr,
            approver=actor,
        ).delete()
        if not deleted:
            raise ChangeRequestNotApplicable("You have not approved this change request")
        enrich_audit(object_version=number)
        return self._to_dict(cr)

    @webhook(
        "change_request.rejected",
        version=_cr_webhook_version,
        details=lambda self, result, bound: self._webhook_cr_details(
            result,
            bound,
            reject_kind="user",
            rejected_reason=result.get("rejected_reason"),
            rejected_by=result.get("rejected_by"),
        ),
    )
    @audit("change_request", operation=OP_REJECT_CHANGE_REQUEST)
    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:write"))
    def reject(self, number: int, reason: str = "") -> dict[str, Any]:
        self._require_feature()
        item = self._item_or_raise()
        self._ensure_write(item)
        cr = ChangeRequest.objects.filter(tree_item=item, number=number).first()
        if cr is None:
            raise ChangeRequestNotFound(f"Change request ~{number} not found")
        if cr.status != ChangeRequest.STATUS_OPEN:
            raise ChangeRequestNotApplicable("Only open change requests can be rejected")
        cr.status = ChangeRequest.STATUS_REJECTED
        cr.rejected_reason = reason[:4096]
        cr.rejected_by = AuthManager.resolve_actor_identity(self.auth)
        cr.rejected_at = timezone.now()
        cr.save()
        enrich_audit(object_version=number)
        return self._to_dict(cr)

    @webhook(
        "change_request.rejected",
        version=_cr_webhook_version,
        details=lambda self, result, bound: self._webhook_cr_details(
            result,
            bound,
            reject_kind="withdrawn",
        ),
    )
    @audit("change_request", operation=OP_WITHDRAW_CHANGE_REQUEST)
    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:read"))
    def withdraw(self, number: int) -> dict[str, Any]:
        self._require_feature()
        item = self._item_or_raise()
        cr = ChangeRequest.objects.filter(tree_item=item, number=number).first()
        if cr is None:
            raise ChangeRequestNotFound(f"Change request ~{number} not found")
        if cr.created_by != AuthManager.resolve_actor_identity(self.auth):
            raise ChangeRequestNotApplicable("Only the author can withdraw this change request")
        if cr.status != ChangeRequest.STATUS_OPEN:
            raise ChangeRequestNotApplicable("Only open change requests can be withdrawn")
        cr.status = ChangeRequest.STATUS_WITHDRAWN
        cr.save(update_fields=["status", "updated_at"])
        enrich_audit(object_version=number)
        return self._to_dict(cr)

    @webhook(
        "change_request.applied",
        version=_cr_webhook_version,
        details=lambda self, result, bound: self._webhook_cr_details(
            result,
            bound,
            applied_version=result.get("applied_version"),
            applied_by=result.get("applied_by"),
        ),
    )
    @audit("change_request", operation=OP_APPLY_CHANGE_REQUEST)
    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:write"))
    def apply(self, number: int) -> dict[str, Any]:
        self._require_feature()
        item = self._item_or_raise()
        self._ensure_write(item)
        LockManager.ensure_path_writable(self.namespace, self.path)
        cr = ChangeRequest.objects.filter(tree_item=item, number=number).select_related("tree_item").first()
        if cr is None:
            raise ChangeRequestNotFound(f"Change request ~{number} not found")
        body = self._plaintext_content(cr)
        if self.body_has_cr_refs(item, body):
            raise ChangeRequestNotApplicable("Cannot apply a change request that references other change requests")
        required = self.namespace.change_requests_required_approvals
        with transaction.atomic():
            cr = ChangeRequest.objects.select_for_update().get(pk=cr.pk)
            if cr.status != ChangeRequest.STATUS_OPEN:
                raise ChangeRequestNotApplicable("Only open change requests can be applied")
            if cr.approvals.count() < required:
                raise ChangeRequestNotApplicable("Insufficient approvals to apply this change request")
            body = self._plaintext_content(cr)
            if not body.strip():
                raise ChangeRequestNotApplicable("Change request content is empty")
            last_ver = item.versions.order_by("-version").first()
            if item.node_type == "secret" and last_ver and last_ver.encrypted_data:
                existing = CryptoManager(self.namespace).decrypt_secret(last_ver.encrypted_data)
                if existing == body:
                    raise ChangeRequestConflict("Change request content is identical to the latest version")
            elif last_ver and getattr(last_ver, "data", None) == body:
                raise ChangeRequestConflict("Change request content is identical to the latest version")
            prev_latest = self._latest_version_number(item)
            tm = TreeManager(self.namespace, self.path, auth=self.auth)
            if item.node_type == "config":
                tm.update_configs(body, skip_change_request_auto_reject=True)
            elif item.node_type == "template":
                tm.update_templates(body, skip_change_request_auto_reject=True)
            elif item.node_type == "secret":
                from .secret import SecretManager

                SecretManager(
                    self.namespace,
                    self.path,
                    secret_obj=item,
                    auth=self.auth,
                ).update(body, skip_change_request_auto_reject=True)
            item.refresh_from_db()
            new_version = self._latest_version_number(item)
            if new_version == prev_latest:
                raise ChangeRequestConflict("Change request content did not produce a new version")
            cr.status = ChangeRequest.STATUS_APPLIED
            cr.applied_version = new_version
            cr.applied_by = AuthManager.resolve_actor_identity(self.auth)
            cr.applied_at = timezone.now()
            cr.save()
            self.rewrite_peer_refs_on_apply(self.namespace, item, number, new_version)
        enrich_audit(object_version=new_version)
        return self._to_dict(cr)

    @audit("change_request", operation=OP_READ_CHANGE_REQUEST)
    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:read"))
    def diff(
        self,
        number: int,
        *,
        against: Literal["base", "latest"] = "base",
        reveal: bool = False,
    ) -> dict[str, Any]:
        self._require_feature()
        stub = self._item_or_raise()
        self._ensure_read(stub)
        cr = ChangeRequest.objects.filter(tree_item_id=stub.pk, number=number).first()
        if cr is None:
            raise ChangeRequestNotFound(f"Change request ~{number} not found")
        item = self._typed_item_for_cr(cr)
        from_ref = "latest" if against == "latest" else str(cr.base_version)
        tm = TreeManager(self.namespace, item.path, auth=self.auth)
        to_ref = f"~{number}"
        from_side = tm._load_diff_side(item, from_ref, reveal)
        to_side = tm._load_diff_side(item, to_ref, reveal)
        decryption_required = item.node_type == "secret" and not reveal
        identical = None
        if not decryption_required:
            identical = from_side.get("data") == to_side.get("data")
        enrich_audit(object_version=number)
        return {
            "path": self.path,
            "to_path": None,
            "from_side": from_side,
            "to_side": to_side,
            "identical": identical,
            "decryption_required": decryption_required,
        }

    @webhook(
        "change_request.comment.created",
        version=_cr_webhook_version,
        details=lambda self, result, bound: {
            **self._webhook_cr_details({}, bound),
            "comment_id": result["id"],
            "author": result["author"],
        },
    )
    @audit("change_request", operation=OP_COMMENT_CHANGE_REQUEST)
    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:read"))
    def add_comment(
        self,
        number: int,
        body: str,
        anchor: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        self._require_feature()
        item = self._item_or_raise()
        self._ensure_read(item)
        cr = self._get_cr_or_raise(number)
        self._ensure_comments_allowed(cr)
        comment = ChangeRequestComment.objects.create(
            change_request=cr,
            author=AuthManager.resolve_actor_identity(self.auth),
            body=body[:8192],
            anchor=anchor,
        )
        enrich_audit(object_version=number)
        return self._comment_to_dict(comment)

    @staticmethod
    def _comment_to_dict(comment: ChangeRequestComment) -> dict[str, Any]:
        return {
            "id": comment.pk,
            "author": comment.author,
            "body": comment.body,
            "anchor": comment.anchor,
            "created_at": comment.created_at,
        }

    def _get_cr_or_raise(self, number: int) -> ChangeRequest:
        item = self._item_or_raise()
        cr = ChangeRequest.objects.filter(tree_item=item, number=number).first()
        if cr is None:
            raise ChangeRequestNotFound(f"Change request ~{number} not found")
        return cr

    def _get_comment_or_raise(self, cr: ChangeRequest, comment_id: int) -> ChangeRequestComment:
        comment = cr.comments.filter(pk=comment_id).first()
        if comment is None:
            raise NotFound(f"Comment {comment_id} not found")
        return comment

    def _ensure_comment_author(self, comment: ChangeRequestComment) -> None:
        if comment.author != AuthManager.resolve_actor_identity(self.auth):
            raise PermissionDenied("Only the comment author can modify this comment")

    @staticmethod
    def _ensure_comments_allowed(cr: ChangeRequest) -> None:
        if cr.status != ChangeRequest.STATUS_OPEN:
            raise ChangeRequestNotApplicable(
                "Comments cannot be added or changed on a closed change request",
            )

    @audit("change_request", operation=OP_UPDATE_CHANGE_REQUEST_COMMENT)
    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:read"))
    def update_comment(self, number: int, comment_id: int, body: str) -> dict[str, Any]:
        self._require_feature()
        item = self._item_or_raise()
        self._ensure_read(item)
        cr = self._get_cr_or_raise(number)
        self._ensure_comments_allowed(cr)
        comment = self._get_comment_or_raise(cr, comment_id)
        self._ensure_comment_author(comment)
        comment.body = body[:8192]
        comment.save(update_fields=["body"])
        enrich_audit(object_version=number)
        return self._comment_to_dict(comment)

    @audit("change_request", operation=OP_DELETE_CHANGE_REQUEST_COMMENT)
    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:read"))
    def delete_comment(self, number: int, comment_id: int) -> None:
        self._require_feature()
        item = self._item_or_raise()
        self._ensure_read(item)
        cr = self._get_cr_or_raise(number)
        self._ensure_comments_allowed(cr)
        comment = self._get_comment_or_raise(cr, comment_id)
        self._ensure_comment_author(comment)
        comment.delete()
        enrich_audit(object_version=number)

    @require_permissions(PermCheck(action=lambda self: f"{self._item_or_raise().node_type}:read"))
    def list_comments(self, number: int, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        self._require_feature()
        item = self._item_or_raise()
        self._ensure_read(item)
        cr = ChangeRequest.objects.filter(tree_item=item, number=number).first()
        if cr is None:
            raise ChangeRequestNotFound(f"Change request ~{number} not found")
        qs = cr.comments.order_by("created_at")
        total = qs.count()
        items = [self._comment_to_dict(c) for c in qs[offset : offset + limit]]
        return {"items": items, "total": total, "limit": limit, "offset": offset}
