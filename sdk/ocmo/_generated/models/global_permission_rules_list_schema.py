from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.global_permission_rule_schema import GlobalPermissionRuleSchema


T = TypeVar("T", bound="GlobalPermissionRulesListSchema")


@_attrs_define
class GlobalPermissionRulesListSchema:
    """
    Attributes:
        rules (List['GlobalPermissionRuleSchema']):
        count (int):
    """

    rules: List["GlobalPermissionRuleSchema"]
    count: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        rules = []
        for rules_item_data in self.rules:
            rules_item = rules_item_data.to_dict()
            rules.append(rules_item)

        count = self.count

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "rules": rules,
                "count": count,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.global_permission_rule_schema import GlobalPermissionRuleSchema

        d = src_dict.copy()
        rules = []
        _rules = d.pop("rules")
        for rules_item_data in _rules:
            rules_item = GlobalPermissionRuleSchema.from_dict(rules_item_data)

            rules.append(rules_item)

        count = d.pop("count")

        global_permission_rules_list_schema = cls(
            rules=rules,
            count=count,
        )

        global_permission_rules_list_schema.additional_properties = d
        return global_permission_rules_list_schema

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
