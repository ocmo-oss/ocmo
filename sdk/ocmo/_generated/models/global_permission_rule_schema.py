import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

if TYPE_CHECKING:
    from ..models.global_permission_rule_schema_rule import GlobalPermissionRuleSchemaRule


T = TypeVar("T", bound="GlobalPermissionRuleSchema")


@_attrs_define
class GlobalPermissionRuleSchema:
    """
    Attributes:
        id (UUID):
        position (float):
        rule (GlobalPermissionRuleSchemaRule):
        created_at (datetime.datetime):
        updated_at (datetime.datetime):
    """

    id: UUID
    position: float
    rule: "GlobalPermissionRuleSchemaRule"
    created_at: datetime.datetime
    updated_at: datetime.datetime
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = str(self.id)

        position = self.position

        rule = self.rule.to_dict()

        created_at = self.created_at.isoformat()

        updated_at = self.updated_at.isoformat()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "position": position,
                "rule": rule,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.global_permission_rule_schema_rule import GlobalPermissionRuleSchemaRule

        d = src_dict.copy()
        id = UUID(d.pop("id"))

        position = d.pop("position")

        rule = GlobalPermissionRuleSchemaRule.from_dict(d.pop("rule"))

        created_at = isoparse(d.pop("created_at"))

        updated_at = isoparse(d.pop("updated_at"))

        global_permission_rule_schema = cls(
            id=id,
            position=position,
            rule=rule,
            created_at=created_at,
            updated_at=updated_at,
        )

        global_permission_rule_schema.additional_properties = d
        return global_permission_rule_schema

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
