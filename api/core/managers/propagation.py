"""Propagation merge logic and manual API entry point."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Literal

from django.conf import settings
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ..decorators.permissions import PermCheck, require_permissions
from ..decorators.webhook import webhook
from ..schemas.propagation import ConfigPropagationSchema
from ..schemas.requests import ConfigOcmoMetadataSchema
from ..shortcuts import (
    align_commented_map_key_order,
    apply_exclude_paths,
    dump_yaml_with_comments,
    is_mapping,
    load_yaml_with_comments,
    to_plain,
)


@dataclass(frozen=True)
class PropagationTargetVersion:
    """Resolved target config version passed in by TreeManager."""

    target_ref: str
    target_path: str
    version_number: int
    version_data: str
    metadata: ConfigOcmoMetadataSchema


class PropagationManager:
    def __init__(self, namespace, source_path: str, auth) -> None:
        self.namespace = namespace
        self.source_path = source_path.strip("/")
        self.auth = auth

    @webhook(
        "propagation.triggered",
        path=lambda self, result, bound: self.source_path,
        version=lambda self, result, bound: result.get("source_version"),
        details=lambda self, result, bound: result,
    )
    @require_permissions(PermCheck("config:read", resource="source_path"))
    def propagate_manual(self, version_ref: str = "latest") -> dict:
        from .tree import TreeManager

        return TreeManager(self.namespace, self.source_path, auth=self.auth).propagate_config(
            version_ref=version_ref, trigger="manual"
        )

    @staticmethod
    def build_source_payload(
        source_metadata: ConfigOcmoMetadataSchema,
        source_body: Any,
        mode: Literal["data", "whole"],
    ) -> Any:
        """Build the propagation payload from parsed source data.

        For ``mode: whole`` this uses Pydantic model_dump (losing ruamel structure).
        Prefer passing ``source_yaml`` to ``plan_propagation`` so that the raw
        YAML CommentedMap is used instead, preserving key order and quoting.
        """
        return PropagationManager._build_source_payload_with_doc(source_metadata, source_body, mode, source_doc=None)

    @staticmethod
    def _build_source_payload_with_doc(
        source_metadata: ConfigOcmoMetadataSchema,
        source_body: Any,
        mode: Literal["data", "whole"],
        source_doc: CommentedMap | None,
    ) -> Any:
        """Build the propagation payload, using raw ruamel doc when available.

        When *source_doc* is provided (``mode: whole`` only) the ``_ocmo`` block
        is taken directly from the parsed YAML, preserving key order, quoting,
        and ruamel scalar styles.  When *source_doc* is ``None`` the block is
        reconstructed from the Pydantic schema (fallback for callers that do not
        supply raw YAML).
        """
        meta_key = settings.OCMO_CONFIG_METADATA_KEY
        body = copy.deepcopy(to_plain(source_body))

        if mode == "data":
            return body if isinstance(body, dict) else body

        if source_doc is not None and meta_key in source_doc:
            raw_ocmo = copy.deepcopy(source_doc[meta_key])
            if isinstance(raw_ocmo, CommentedMap):
                raw_ocmo.pop("propagation", None)
            else:
                raw_ocmo = {k: v for k, v in to_plain(raw_ocmo).items() if k != "propagation"}
            if isinstance(body, dict):
                payload = dict(body)
                payload[meta_key] = raw_ocmo
                return payload
            return {meta_key: raw_ocmo, "data": body}

        # Fallback: reconstruct _ocmo from Pydantic (loses ruamel structure)
        stripped_metadata = source_metadata.model_copy(update={"propagation": None})
        ocmo_dict = stripped_metadata.model_dump(
            exclude_none=True,
            exclude_defaults=True,
        )
        if isinstance(body, dict):
            payload = dict(body)
            if ocmo_dict:
                payload[meta_key] = ocmo_dict
            return payload
        if ocmo_dict:
            return {meta_key: ocmo_dict, "data": body}
        return body

    @classmethod
    def plan_propagation(
        cls,
        *,
        source_metadata: ConfigOcmoMetadataSchema,
        source_body: Any,
        rules: ConfigPropagationSchema,
        targets: list[PropagationTargetVersion],
        source_yaml: str = "",
    ) -> list[dict]:
        """Return per-target outcomes with merged YAML for targets that need updates."""
        source_doc: CommentedMap | None = None
        if source_yaml:
            raw = load_yaml_with_comments(source_yaml)
            if isinstance(raw, CommentedMap):
                source_doc = raw

        source_payload = cls._build_source_payload_with_doc(source_metadata, source_body, rules.mode, source_doc)
        apply_exclude_paths(source_payload, rules.exclude)

        outcomes: list[dict] = []
        for target in targets:
            merged_yaml = cls.merge_target(
                target.version_data,
                target.metadata,
                source_payload,
                rules.mode,
                source_doc=source_doc,
            )
            if merged_yaml == target.version_data:
                outcomes.append(
                    {
                        "path": target.target_ref,
                        "status": "unchanged",
                        "version": target.version_number,
                    }
                )
                continue
            outcomes.append(
                {
                    "path": target.target_ref,
                    "status": "updated",
                    "target_path": target.target_path,
                    "merged_yaml": merged_yaml,
                    "version": target.version_number,
                }
            )
        return outcomes

    @classmethod
    def merge_target(
        cls,
        target_yaml: str,
        target_metadata: ConfigOcmoMetadataSchema,
        source_payload: Any,
        mode: Literal["data", "whole"],
        source_doc: CommentedMap | None = None,
    ) -> str:
        meta_key = settings.OCMO_CONFIG_METADATA_KEY
        target_doc = load_yaml_with_comments(target_yaml)
        if not isinstance(target_doc, CommentedMap):
            target_doc = CommentedMap({"data": to_plain(target_doc)})

        # Separate data body from _ocmo.  Keep source_ocmo as-is (may be
        # CommentedMap when source_doc was provided) so ruamel structure is
        # preserved during merge.
        source_ocmo: Any = None
        if isinstance(source_payload, dict):
            source_body_part: Any = {k: v for k, v in source_payload.items() if k != meta_key}
            source_ocmo = source_payload.get(meta_key)
        else:
            source_body_part = to_plain(source_payload)

        if mode == "data":
            if is_mapping(source_body_part):
                cls._prop_merge_in_place(target_doc, source_body_part)
        else:
            target_ocmo = target_doc.get(meta_key)
            if target_ocmo is None:
                target_ocmo = CommentedMap()
                target_doc[meta_key] = target_ocmo
            elif not isinstance(target_ocmo, CommentedMap):
                target_ocmo = CommentedMap(to_plain(target_ocmo))
                target_doc[meta_key] = target_ocmo

            if is_mapping(source_body_part):
                cls._prop_merge_in_place(target_doc, source_body_part)
            if source_ocmo is not None and is_mapping(source_ocmo):
                ocmo_to_merge = {k: v for k, v in source_ocmo.items() if k != "propagation"}
                if ocmo_to_merge:
                    cls._prop_merge_in_place(target_ocmo, ocmo_to_merge)
            if target_metadata.propagation is None and "propagation" in target_ocmo:
                target_ocmo.pop("propagation", None)

            # Reorder whole document to match source key order (fixes _ocmo position)
            if source_doc is not None:
                align_commented_map_key_order(target_doc, source_doc)

        return dump_yaml_with_comments(target_doc)

    @classmethod
    def _prop_merge_in_place(cls, target: Any, updater: Any) -> None:
        """Merge *updater* into *target* CommentedMap with propagation semantics.

        - Mapping + mapping: recurse.
        - List, scalar, or type mismatch: source value **replaces** target value
          (unlike extend's list-concatenation semantics).
        - New keys are deep-copied from the updater.
        """
        if not isinstance(target, CommentedMap) or not is_mapping(updater):
            return
        for key, value in updater.items():
            if key not in target:
                target[key] = copy.deepcopy(value)
                continue
            existing = target[key]
            if isinstance(existing, CommentedMap) and is_mapping(value):
                cls._prop_merge_in_place(existing, value)
            else:
                # Replace: list, scalar, or type mismatch.
                # Use isinstance check on value directly so ruamel scalar types
                # (e.g. DoubleQuotedScalarString) are preserved via deepcopy.
                if isinstance(value, (CommentedSeq, list)):
                    target[key] = CommentedSeq(copy.deepcopy(to_plain(value)))
                else:
                    target[key] = copy.deepcopy(value)
