import datetime
from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="ResolveSeriesBucketSchema")


@_attrs_define
class ResolveSeriesBucketSchema:
    """
    Attributes:
        start (datetime.datetime):
        direct (Union[Unset, int]):  Default: 0.
        nested (Union[Unset, int]):  Default: 0.
        errors (Union[Unset, int]):  Default: 0.
    """

    start: datetime.datetime
    direct: Union[Unset, int] = 0
    nested: Union[Unset, int] = 0
    errors: Union[Unset, int] = 0
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        start = self.start.isoformat()

        direct = self.direct

        nested = self.nested

        errors = self.errors

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "start": start,
            }
        )
        if direct is not UNSET:
            field_dict["direct"] = direct
        if nested is not UNSET:
            field_dict["nested"] = nested
        if errors is not UNSET:
            field_dict["errors"] = errors

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        start = isoparse(d.pop("start"))

        direct = d.pop("direct", UNSET)

        nested = d.pop("nested", UNSET)

        errors = d.pop("errors", UNSET)

        resolve_series_bucket_schema = cls(
            start=start,
            direct=direct,
            nested=nested,
            errors=errors,
        )

        resolve_series_bucket_schema.additional_properties = d
        return resolve_series_bucket_schema

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
