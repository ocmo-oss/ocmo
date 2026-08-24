from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="PublicOidcAuthSchema")


@_attrs_define
class PublicOidcAuthSchema:
    """Browser-facing OIDC settings for interactive clients (SPA, CLI auth code flow).

    Attributes:
        issuer (str): OIDC issuer URL (authority for discovery)
        client_id (str): OAuth2 client id for the browser SPA and interactive CLI device login
        authorization_url (str): OAuth2 authorization endpoint
        token_url (str): OAuth2 token endpoint
        scopes (str): Space-separated OAuth2 scopes requested by OCMO clients
    """

    issuer: str
    client_id: str
    authorization_url: str
    token_url: str
    scopes: str
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        issuer = self.issuer

        client_id = self.client_id

        authorization_url = self.authorization_url

        token_url = self.token_url

        scopes = self.scopes

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "issuer": issuer,
                "client_id": client_id,
                "authorization_url": authorization_url,
                "token_url": token_url,
                "scopes": scopes,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        issuer = d.pop("issuer")

        client_id = d.pop("client_id")

        authorization_url = d.pop("authorization_url")

        token_url = d.pop("token_url")

        scopes = d.pop("scopes")

        public_oidc_auth_schema = cls(
            issuer=issuer,
            client_id=client_id,
            authorization_url=authorization_url,
            token_url=token_url,
            scopes=scopes,
        )

        public_oidc_auth_schema.additional_properties = d
        return public_oidc_auth_schema

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
