from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.change_request_referrer_schema_node_type import ChangeRequestReferrerSchemaNodeType

T = TypeVar("T", bound="ChangeRequestReferrerSchema")


@_attrs_define
class ChangeRequestReferrerSchema:
    """
    Attributes:
        path (str):
        node_type (ChangeRequestReferrerSchemaNodeType):
        number (int):
    """

    path: str
    node_type: ChangeRequestReferrerSchemaNodeType
    number: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        path = self.path

        node_type = self.node_type.value

        number = self.number

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "path": path,
                "node_type": node_type,
                "number": number,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        path = d.pop("path")

        node_type = ChangeRequestReferrerSchemaNodeType(d.pop("node_type"))

        number = d.pop("number")

        change_request_referrer_schema = cls(
            path=path,
            node_type=node_type,
            number=number,
        )

        change_request_referrer_schema.additional_properties = d
        return change_request_referrer_schema

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
