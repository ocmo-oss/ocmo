from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ResolvedParameterSchema")


@_attrs_define
class ResolvedParameterSchema:
    """One parameter row in the `/~resolve-parameters/` debug response.

    Attributes:
        type (str):
        description (Union[Unset, str]):  Default: ''.
        selector (Union[None, Unset, str]):
        secret_reference (Union[None, Unset, str]):
        declared_default (Union[Any, None, Unset]):
        raw_value (Union[Any, None, Unset]):
        effective_value (Union[Any, None, Unset]):
        transformers_applied (Union[Unset, List[str]]):
        caller_supplied (Union[None, Unset, bool]):
    """

    type: str
    description: Union[Unset, str] = ""
    selector: Union[None, Unset, str] = UNSET
    secret_reference: Union[None, Unset, str] = UNSET
    declared_default: Union[Any, None, Unset] = UNSET
    raw_value: Union[Any, None, Unset] = UNSET
    effective_value: Union[Any, None, Unset] = UNSET
    transformers_applied: Union[Unset, List[str]] = UNSET
    caller_supplied: Union[None, Unset, bool] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        type = self.type

        description = self.description

        selector: Union[None, Unset, str]
        if isinstance(self.selector, Unset):
            selector = UNSET
        else:
            selector = self.selector

        secret_reference: Union[None, Unset, str]
        if isinstance(self.secret_reference, Unset):
            secret_reference = UNSET
        else:
            secret_reference = self.secret_reference

        declared_default: Union[Any, None, Unset]
        if isinstance(self.declared_default, Unset):
            declared_default = UNSET
        else:
            declared_default = self.declared_default

        raw_value: Union[Any, None, Unset]
        if isinstance(self.raw_value, Unset):
            raw_value = UNSET
        else:
            raw_value = self.raw_value

        effective_value: Union[Any, None, Unset]
        if isinstance(self.effective_value, Unset):
            effective_value = UNSET
        else:
            effective_value = self.effective_value

        transformers_applied: Union[Unset, List[str]] = UNSET
        if not isinstance(self.transformers_applied, Unset):
            transformers_applied = self.transformers_applied

        caller_supplied: Union[None, Unset, bool]
        if isinstance(self.caller_supplied, Unset):
            caller_supplied = UNSET
        else:
            caller_supplied = self.caller_supplied

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type,
            }
        )
        if description is not UNSET:
            field_dict["description"] = description
        if selector is not UNSET:
            field_dict["selector"] = selector
        if secret_reference is not UNSET:
            field_dict["secret_reference"] = secret_reference
        if declared_default is not UNSET:
            field_dict["declared_default"] = declared_default
        if raw_value is not UNSET:
            field_dict["raw_value"] = raw_value
        if effective_value is not UNSET:
            field_dict["effective_value"] = effective_value
        if transformers_applied is not UNSET:
            field_dict["transformers_applied"] = transformers_applied
        if caller_supplied is not UNSET:
            field_dict["caller_supplied"] = caller_supplied

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        type = d.pop("type")

        description = d.pop("description", UNSET)

        def _parse_selector(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        selector = _parse_selector(d.pop("selector", UNSET))

        def _parse_secret_reference(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        secret_reference = _parse_secret_reference(d.pop("secret_reference", UNSET))

        def _parse_declared_default(data: object) -> Union[Any, None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[Any, None, Unset], data)

        declared_default = _parse_declared_default(d.pop("declared_default", UNSET))

        def _parse_raw_value(data: object) -> Union[Any, None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[Any, None, Unset], data)

        raw_value = _parse_raw_value(d.pop("raw_value", UNSET))

        def _parse_effective_value(data: object) -> Union[Any, None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[Any, None, Unset], data)

        effective_value = _parse_effective_value(d.pop("effective_value", UNSET))

        transformers_applied = cast(List[str], d.pop("transformers_applied", UNSET))

        def _parse_caller_supplied(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        caller_supplied = _parse_caller_supplied(d.pop("caller_supplied", UNSET))

        resolved_parameter_schema = cls(
            type=type,
            description=description,
            selector=selector,
            secret_reference=secret_reference,
            declared_default=declared_default,
            raw_value=raw_value,
            effective_value=effective_value,
            transformers_applied=transformers_applied,
            caller_supplied=caller_supplied,
        )

        resolved_parameter_schema.additional_properties = d
        return resolved_parameter_schema

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
