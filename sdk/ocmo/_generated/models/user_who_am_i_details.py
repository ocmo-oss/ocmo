from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.user_who_am_i_details_claims import UserWhoAmIDetailsClaims


T = TypeVar("T", bound="UserWhoAmIDetails")


@_attrs_define
class UserWhoAmIDetails:
    """OIDC-specific identity fields.

    Attributes:
        is_global_admin (bool): Whether the user matches OIDC global-admin claim/value
        email (Union[Any, None, Unset]): OIDC email claim
        claims (Union[Unset, UserWhoAmIDetailsClaims]): All OIDC JWT claims (excluding internal fields)
    """

    is_global_admin: bool
    email: Union[Any, None, Unset] = UNSET
    claims: Union[Unset, "UserWhoAmIDetailsClaims"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        is_global_admin = self.is_global_admin

        email: Union[Any, None, Unset]
        if isinstance(self.email, Unset):
            email = UNSET
        else:
            email = self.email

        claims: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.claims, Unset):
            claims = self.claims.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "is_global_admin": is_global_admin,
            }
        )
        if email is not UNSET:
            field_dict["email"] = email
        if claims is not UNSET:
            field_dict["claims"] = claims

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.user_who_am_i_details_claims import UserWhoAmIDetailsClaims

        d = src_dict.copy()
        is_global_admin = d.pop("is_global_admin")

        def _parse_email(data: object) -> Union[Any, None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[Any, None, Unset], data)

        email = _parse_email(d.pop("email", UNSET))

        _claims = d.pop("claims", UNSET)
        claims: Union[Unset, UserWhoAmIDetailsClaims]
        if isinstance(_claims, Unset):
            claims = UNSET
        else:
            claims = UserWhoAmIDetailsClaims.from_dict(_claims)

        user_who_am_i_details = cls(
            is_global_admin=is_global_admin,
            email=email,
            claims=claims,
        )

        user_who_am_i_details.additional_properties = d
        return user_who_am_i_details

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
