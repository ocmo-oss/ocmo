from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.cast_format_schema import CastFormatSchema


T = TypeVar("T", bound="CastFormatsListSchema")


@_attrs_define
class CastFormatsListSchema:
    """
    Attributes:
        formats (List['CastFormatSchema']):
    """

    formats: List["CastFormatSchema"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        formats = []
        for formats_item_data in self.formats:
            formats_item = formats_item_data.to_dict()
            formats.append(formats_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "formats": formats,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.cast_format_schema import CastFormatSchema

        d = src_dict.copy()
        formats = []
        _formats = d.pop("formats")
        for formats_item_data in _formats:
            formats_item = CastFormatSchema.from_dict(formats_item_data)

            formats.append(formats_item)

        cast_formats_list_schema = cls(
            formats=formats,
        )

        cast_formats_list_schema.additional_properties = d
        return cast_formats_list_schema

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
