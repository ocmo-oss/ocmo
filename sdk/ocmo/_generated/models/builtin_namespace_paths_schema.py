from typing import Any, Dict, List, Type, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="BuiltinNamespacePathsSchema")


@_attrs_define
class BuiltinNamespacePathsSchema:
    """
    Attributes:
        config (List[str]): Built-in namespace config paths (e.g. _permissions)
        secret (List[str]): Built-in namespace secret paths
        schema (List[str]): Built-in namespace schema config paths
        order (List[str]): Preferred display order for built-in namespace items in the tree
    """

    config: List[str]
    secret: List[str]
    schema: List[str]
    order: List[str]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        config = self.config

        secret = self.secret

        schema = self.schema

        order = self.order

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "config": config,
                "secret": secret,
                "schema": schema,
                "order": order,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        config = cast(List[str], d.pop("config"))

        secret = cast(List[str], d.pop("secret"))

        schema = cast(List[str], d.pop("schema"))

        order = cast(List[str], d.pop("order"))

        builtin_namespace_paths_schema = cls(
            config=config,
            secret=secret,
            schema=schema,
            order=order,
        )

        builtin_namespace_paths_schema.additional_properties = d
        return builtin_namespace_paths_schema

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
