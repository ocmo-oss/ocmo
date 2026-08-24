from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.cast_format_schema_options_schema import CastFormatSchemaOptionsSchema


T = TypeVar("T", bound="CastFormatSchema")


@_attrs_define
class CastFormatSchema:
    """One supported cast output format and its option JSON Schema.

    Attributes:
        format_ (str): Cast format identifier (yaml, json, env, …)
        options_schema (CastFormatSchemaOptionsSchema): JSON Schema for ``cast_option_*`` query parameters
    """

    format_: str
    options_schema: "CastFormatSchemaOptionsSchema"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        format_ = self.format_

        options_schema = self.options_schema.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "format": format_,
                "options_schema": options_schema,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.cast_format_schema_options_schema import CastFormatSchemaOptionsSchema

        d = src_dict.copy()
        format_ = d.pop("format")

        options_schema = CastFormatSchemaOptionsSchema.from_dict(d.pop("options_schema"))

        cast_format_schema = cls(
            format_=format_,
            options_schema=options_schema,
        )

        cast_format_schema.additional_properties = d
        return cast_format_schema

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
