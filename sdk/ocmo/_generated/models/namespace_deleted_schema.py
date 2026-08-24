from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="NamespaceDeletedSchema")


@_attrs_define
class NamespaceDeletedSchema:
    """Confirmation payload for a successful namespace deletion.

    Attributes:
        namespace (str): Canonical name of the namespace that was removed
        success (Union[Unset, bool]): Deletion completed successfully Default: True.
    """

    namespace: str
    success: Union[Unset, bool] = True
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        namespace = self.namespace

        success = self.success

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "namespace": namespace,
            }
        )
        if success is not UNSET:
            field_dict["success"] = success

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        namespace = d.pop("namespace")

        success = d.pop("success", UNSET)

        namespace_deleted_schema = cls(
            namespace=namespace,
            success=success,
        )

        namespace_deleted_schema.additional_properties = d
        return namespace_deleted_schema

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
