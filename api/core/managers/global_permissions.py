import builtins
import uuid

from django.core.exceptions import ValidationError
from django.db.models import Count, Max

from ..constants.audit_operations import (
    OP_CREATE_PERMISSION,
    OP_DELETE_PERMISSION,
    OP_LIST_PERMISSIONS,
    OP_MOVE_PERMISSION,
    OP_READ_PERMISSION,
    OP_UPDATE_PERMISSION,
)
from ..decorators import arg, audit, require_permissions
from ..models import GlobalPermissionRule
from ..schemas import GlobalPermissionRulePayload
from ..utils.permissions_compiler import PermissionsCompiler

CATCH_ALL_POSITION = 999.0


def _is_catch_all_rule(rule_data: dict) -> bool:
    return PermissionsCompiler.is_catch_all_namespace_pattern(
        rule_data.get("namespace", "*"),
    )


def _next_non_catch_all_position() -> float:
    last = GlobalPermissionRule.objects.filter(position__lt=CATCH_ALL_POSITION).order_by("-position").first()
    return (last.position + 1.0) if last else 1.0


def _position_for_rule(rule_data: dict, *, requested: float | None = None) -> float:
    if _is_catch_all_rule(rule_data):
        return CATCH_ALL_POSITION
    if requested is not None:
        if requested >= CATCH_ALL_POSITION:
            raise ValidationError(f"Position must be less than {CATCH_ALL_POSITION:g} for non-catch-all rules")
        return requested
    return _next_non_catch_all_position()


def _ordered_rule_dicts_after_insert(rule_data: dict, position: float) -> list[dict]:
    """Return evaluation order after inserting *rule_data* at *position*."""
    rows = list(GlobalPermissionRule.objects.order_by("position", "id"))
    insert_at = sum(1 for row in rows if row.position <= position)
    ordered = [row.rule for row in rows]
    ordered.insert(insert_at, rule_data)
    return ordered


def _validated_rule_dict(payload: GlobalPermissionRulePayload) -> dict:
    rule_data = payload.to_rule_dict()
    try:
        PermissionsCompiler.compile_global_rules([rule_data])
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    return rule_data


def _resolve_rule_ref(rule_id: str) -> GlobalPermissionRule:
    """Resolve a rule by database UUID or user-defined ``rule.id``."""
    ref = rule_id.strip()
    if not ref:
        raise GlobalPermissionRule.DoesNotExist("Rule  not found")

    try:
        rule_uuid = uuid.UUID(ref)
    except ValueError:
        rule_uuid = None

    if rule_uuid is not None:
        try:
            return GlobalPermissionRule.objects.get(id=rule_uuid)
        except GlobalPermissionRule.DoesNotExist:
            pass

    matches = list(GlobalPermissionRule.objects.filter(rule__id=ref))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValidationError(f"Multiple global permission rules match id {ref!r}.")
    raise GlobalPermissionRule.DoesNotExist(f"Rule {rule_id} not found")


class GlobalPermissionsManager:
    """CRUD operations for Global Permission rules."""

    def __init__(self, *, auth):
        self.auth = auth

    @staticmethod
    def cache_signature() -> tuple[int, int]:
        """Return ``(rule_count, latest_updated_at_ms)`` for compiler cache keys."""
        agg = GlobalPermissionRule.objects.aggregate(
            count=Count("id"),
            latest=Max("updated_at"),
        )
        count = agg["count"] or 0
        latest_ms = int(agg["latest"].timestamp() * 1000) if agg["latest"] else 0
        return count, latest_ms

    @staticmethod
    def ordered_rule_dicts() -> list[dict]:
        """Return global permission rule payloads in evaluation order."""
        return [row.rule for row in GlobalPermissionRule.objects.order_by("position", "id")]

    @audit("global_permission", object_id_attr="*", operation=OP_LIST_PERMISSIONS)
    @require_permissions("global:admin")
    def list(self, *, limit=100, offset=0) -> dict:
        qs = GlobalPermissionRule.objects.order_by("position", "id")
        count = qs.count()
        rules = list(qs[offset : offset + limit])
        return {"rules": rules, "count": count}

    @audit("global_permission", object_id_attr=arg("rule_id"), operation=OP_READ_PERMISSION)
    @require_permissions("global:admin")
    def get(self, rule_id: str) -> GlobalPermissionRule:
        return _resolve_rule_ref(rule_id)

    @audit("global_permission", object_id_attr="", operation=OP_CREATE_PERMISSION)
    @require_permissions("global:admin")
    def create(self, payload) -> GlobalPermissionRule:
        rule_data = _validated_rule_dict(payload)
        position = _position_for_rule(rule_data)
        self._validate_full_rules_order(_ordered_rule_dicts_after_insert(rule_data, position))
        return GlobalPermissionRule.objects.create(position=position, rule=rule_data)

    @audit(
        "global_permission",
        object_id_attr=arg("rule_id"),
        operation=OP_UPDATE_PERMISSION,
    )
    @require_permissions("global:admin")
    def update(self, rule_id: str, payload) -> GlobalPermissionRule:
        rule_obj = _resolve_rule_ref(rule_id)
        rule_data = _validated_rule_dict(payload)
        rows = list(GlobalPermissionRule.objects.order_by("position", "id"))
        ordered = [rule_data if row.id == rule_obj.id else row.rule for row in rows]
        self._validate_full_rules_order(ordered)
        rule_obj.rule = rule_data
        if _is_catch_all_rule(rule_data):
            rule_obj.position = CATCH_ALL_POSITION
        elif rule_obj.position >= CATCH_ALL_POSITION:
            rule_obj.position = _next_non_catch_all_position()
        rule_obj.save()
        return rule_obj

    @audit(
        "global_permission",
        object_id_attr=arg("rule_id"),
        operation=OP_DELETE_PERMISSION,
    )
    @require_permissions("global:admin")
    def delete(self, rule_id: str) -> None:
        _resolve_rule_ref(rule_id).delete()

    @audit(
        "global_permission",
        object_id_attr=arg("rule_id"),
        operation=OP_MOVE_PERMISSION,
    )
    @require_permissions("global:admin")
    def move(self, rule_id: str, position: float) -> GlobalPermissionRule:
        rule_obj = _resolve_rule_ref(rule_id)
        new_position = _position_for_rule(rule_obj.rule, requested=position)
        for row in GlobalPermissionRule.objects.filter(
            position__gte=new_position,
            position__lt=CATCH_ALL_POSITION,
        ).exclude(id=rule_obj.id):
            row.position += 1.0
            row.save()
        rule_obj.position = new_position
        rule_obj.save()
        self._validate_full_rules_order(self.ordered_rule_dicts())
        return rule_obj

    def _validate_full_rules_order(self, rule_dicts: builtins.list[dict]) -> None:
        try:
            PermissionsCompiler.validate_global_rules_order(rule_dicts)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
