from typing import TYPE_CHECKING, Any, Dict, List, Literal, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.user_who_am_i_details import UserWhoAmIDetails


T = TypeVar("T", bound="UserWhoAmISchema")


@_attrs_define
class UserWhoAmISchema:
    """Authenticated OIDC user identity.

    Attributes:
        auth_type (Literal['user']): Authentication method: OIDC user
        identifier (Any): OIDC subject or configured user id claim
        display_name (Any): Human-readable identity label
        user_details (UserWhoAmIDetails): OIDC-specific identity fields.
        access_scope (Union[Unset, str]): Subtree scope for tree operations; empty for OIDC users Default: ''.
    """

    auth_type: Literal["user"]
    identifier: Any
    display_name: Any
    user_details: "UserWhoAmIDetails"
    access_scope: Union[Unset, str] = ""
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        auth_type = self.auth_type

        identifier = self.identifier

        display_name = self.display_name

        user_details = self.user_details.to_dict()

        access_scope = self.access_scope

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "auth_type": auth_type,
                "identifier": identifier,
                "display_name": display_name,
                "user_details": user_details,
            }
        )
        if access_scope is not UNSET:
            field_dict["access_scope"] = access_scope

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.user_who_am_i_details import UserWhoAmIDetails

        d = src_dict.copy()
        auth_type = cast(Literal["user"], d.pop("auth_type"))
        if auth_type != "user":
            raise ValueError(f"auth_type must match const 'user', got '{auth_type}'")

        identifier = d.pop("identifier")

        display_name = d.pop("display_name")

        user_details = UserWhoAmIDetails.from_dict(d.pop("user_details"))

        access_scope = d.pop("access_scope", UNSET)

        user_who_am_i_schema = cls(
            auth_type=auth_type,
            identifier=identifier,
            display_name=display_name,
            user_details=user_details,
            access_scope=access_scope,
        )

        user_who_am_i_schema.additional_properties = d
        return user_who_am_i_schema

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
