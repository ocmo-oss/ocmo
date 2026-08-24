from typing import TYPE_CHECKING, Any, Dict, List, Literal, Type, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.resolver_who_am_i_details import ResolverWhoAmIDetails


T = TypeVar("T", bound="ResolverWhoAmISchema")


@_attrs_define
class ResolverWhoAmISchema:
    """Authenticated resolver service-account identity.

    Attributes:
        auth_type (Literal['resolver']): Authentication method: resolver service account
        identifier (Any): Full resolver tree path (<access_scope>/<name>)
        display_name (Any): Human-readable identity label
        access_scope (str): Resolver subtree scope path
        resolver_details (ResolverWhoAmIDetails): Resolver service-account fields.
    """

    auth_type: Literal["resolver"]
    identifier: Any
    display_name: Any
    access_scope: str
    resolver_details: "ResolverWhoAmIDetails"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        auth_type = self.auth_type

        identifier = self.identifier

        display_name = self.display_name

        access_scope = self.access_scope

        resolver_details = self.resolver_details.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "auth_type": auth_type,
                "identifier": identifier,
                "display_name": display_name,
                "access_scope": access_scope,
                "resolver_details": resolver_details,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.resolver_who_am_i_details import ResolverWhoAmIDetails

        d = src_dict.copy()
        auth_type = cast(Literal["resolver"], d.pop("auth_type"))
        if auth_type != "resolver":
            raise ValueError(f"auth_type must match const 'resolver', got '{auth_type}'")

        identifier = d.pop("identifier")

        display_name = d.pop("display_name")

        access_scope = d.pop("access_scope")

        resolver_details = ResolverWhoAmIDetails.from_dict(d.pop("resolver_details"))

        resolver_who_am_i_schema = cls(
            auth_type=auth_type,
            identifier=identifier,
            display_name=display_name,
            access_scope=access_scope,
            resolver_details=resolver_details,
        )

        resolver_who_am_i_schema.additional_properties = d
        return resolver_who_am_i_schema

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
