from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="EffectiveResolverHooksSchema")


@_attrs_define
class EffectiveResolverHooksSchema:
    """Hook commands from the effective resolver configuration.

    Attributes:
        validate (Union[None, Unset, str]):
        validate_all (Union[None, Unset, str]):
        post_resolve (Union[None, Unset, str]):
        post_resolve_all (Union[None, Unset, str]):
    """

    validate: Union[None, Unset, str] = UNSET
    validate_all: Union[None, Unset, str] = UNSET
    post_resolve: Union[None, Unset, str] = UNSET
    post_resolve_all: Union[None, Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        validate: Union[None, Unset, str]
        if isinstance(self.validate, Unset):
            validate = UNSET
        else:
            validate = self.validate

        validate_all: Union[None, Unset, str]
        if isinstance(self.validate_all, Unset):
            validate_all = UNSET
        else:
            validate_all = self.validate_all

        post_resolve: Union[None, Unset, str]
        if isinstance(self.post_resolve, Unset):
            post_resolve = UNSET
        else:
            post_resolve = self.post_resolve

        post_resolve_all: Union[None, Unset, str]
        if isinstance(self.post_resolve_all, Unset):
            post_resolve_all = UNSET
        else:
            post_resolve_all = self.post_resolve_all

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if validate is not UNSET:
            field_dict["validate"] = validate
        if validate_all is not UNSET:
            field_dict["validate_all"] = validate_all
        if post_resolve is not UNSET:
            field_dict["post_resolve"] = post_resolve
        if post_resolve_all is not UNSET:
            field_dict["post_resolve_all"] = post_resolve_all

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()

        def _parse_validate(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        validate = _parse_validate(d.pop("validate", UNSET))

        def _parse_validate_all(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        validate_all = _parse_validate_all(d.pop("validate_all", UNSET))

        def _parse_post_resolve(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        post_resolve = _parse_post_resolve(d.pop("post_resolve", UNSET))

        def _parse_post_resolve_all(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        post_resolve_all = _parse_post_resolve_all(d.pop("post_resolve_all", UNSET))

        effective_resolver_hooks_schema = cls(
            validate=validate,
            validate_all=validate_all,
            post_resolve=post_resolve,
            post_resolve_all=post_resolve_all,
        )

        effective_resolver_hooks_schema.additional_properties = d
        return effective_resolver_hooks_schema

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
