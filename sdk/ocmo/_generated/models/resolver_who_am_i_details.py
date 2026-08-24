from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ResolverWhoAmIDetails")


@_attrs_define
class ResolverWhoAmIDetails:
    """Resolver service-account fields.

    Attributes:
        namespace (str): Namespace name
        name (str): Resolver leaf name
        token_number (int): Which resolver token (1 or 2) authenticated the request
    """

    namespace: str
    name: str
    token_number: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        namespace = self.namespace

        name = self.name

        token_number = self.token_number

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "namespace": namespace,
                "name": name,
                "token_number": token_number,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        namespace = d.pop("namespace")

        name = d.pop("name")

        token_number = d.pop("token_number")

        resolver_who_am_i_details = cls(
            namespace=namespace,
            name=name,
            token_number=token_number,
        )

        resolver_who_am_i_details.additional_properties = d
        return resolver_who_am_i_details

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
