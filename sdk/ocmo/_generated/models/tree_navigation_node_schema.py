from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="TreeNavigationNodeSchema")


@_attrs_define
class TreeNavigationNodeSchema:
    """Minimal tree node metadata for navigate/search (UI tree browser).

    Attributes:
        name (str): Leaf segment name
        path (str): Full path within the namespace
        node_type (str): Item type discriminator
    """

    name: str
    path: str
    node_type: str
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name = self.name

        path = self.path

        node_type = self.node_type

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "path": path,
                "node_type": node_type,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        name = d.pop("name")

        path = d.pop("path")

        node_type = d.pop("node_type")

        tree_navigation_node_schema = cls(
            name=name,
            path=path,
            node_type=node_type,
        )

        tree_navigation_node_schema.additional_properties = d
        return tree_navigation_node_schema

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
