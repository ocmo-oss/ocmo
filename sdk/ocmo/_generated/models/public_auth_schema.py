from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.public_oidc_auth_schema import PublicOidcAuthSchema


T = TypeVar("T", bound="PublicAuthSchema")


@_attrs_define
class PublicAuthSchema:
    """Public OIDC settings for frontend, SDK, and CLI bootstrap.

    Attributes:
        oidc (PublicOidcAuthSchema): Browser-facing OIDC settings for interactive clients (SPA, CLI auth code flow).
    """

    oidc: "PublicOidcAuthSchema"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        oidc = self.oidc.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "oidc": oidc,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.public_oidc_auth_schema import PublicOidcAuthSchema

        d = src_dict.copy()
        oidc = PublicOidcAuthSchema.from_dict(d.pop("oidc"))

        public_auth_schema = cls(
            oidc=oidc,
        )

        public_auth_schema.additional_properties = d
        return public_auth_schema

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
