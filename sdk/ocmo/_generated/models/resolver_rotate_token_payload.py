from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.resolver_rotate_token_payload_token_number import ResolverRotateTokenPayloadTokenNumber

T = TypeVar("T", bound="ResolverRotateTokenPayload")


@_attrs_define
class ResolverRotateTokenPayload:
    """Body for resolver token rotation.

    Attributes:
        token_number (ResolverRotateTokenPayloadTokenNumber): Which token slot to rotate (1 or 2)
    """

    token_number: ResolverRotateTokenPayloadTokenNumber
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        token_number = self.token_number.value

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "token_number": token_number,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        token_number = ResolverRotateTokenPayloadTokenNumber(d.pop("token_number"))

        resolver_rotate_token_payload = cls(
            token_number=token_number,
        )

        resolver_rotate_token_payload.additional_properties = d
        return resolver_rotate_token_payload

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
