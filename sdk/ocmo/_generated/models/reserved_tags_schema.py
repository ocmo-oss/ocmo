from typing import Any, Dict, List, Type, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ReservedTagsSchema")


@_attrs_define
class ReservedTagsSchema:
    """
    Attributes:
        config (List[str]): Reserved tag names for configs
        template (List[str]): Reserved tag names for templates
        secret (List[str]): Reserved tag names for secrets
    """

    config: List[str]
    template: List[str]
    secret: List[str]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        config = self.config

        template = self.template

        secret = self.secret

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "config": config,
                "template": template,
                "secret": secret,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        config = cast(List[str], d.pop("config"))

        template = cast(List[str], d.pop("template"))

        secret = cast(List[str], d.pop("secret"))

        reserved_tags_schema = cls(
            config=config,
            template=template,
            secret=secret,
        )

        reserved_tags_schema.additional_properties = d
        return reserved_tags_schema

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
