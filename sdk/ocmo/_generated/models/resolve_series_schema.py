from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.resolve_series_bucket_schema import ResolveSeriesBucketSchema


T = TypeVar("T", bound="ResolveSeriesSchema")


@_attrs_define
class ResolveSeriesSchema:
    """
    Attributes:
        bucket_seconds (int):
        buckets (List['ResolveSeriesBucketSchema']):
    """

    bucket_seconds: int
    buckets: List["ResolveSeriesBucketSchema"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        bucket_seconds = self.bucket_seconds

        buckets = []
        for buckets_item_data in self.buckets:
            buckets_item = buckets_item_data.to_dict()
            buckets.append(buckets_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "bucket_seconds": bucket_seconds,
                "buckets": buckets,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.resolve_series_bucket_schema import ResolveSeriesBucketSchema

        d = src_dict.copy()
        bucket_seconds = d.pop("bucket_seconds")

        buckets = []
        _buckets = d.pop("buckets")
        for buckets_item_data in _buckets:
            buckets_item = ResolveSeriesBucketSchema.from_dict(buckets_item_data)

            buckets.append(buckets_item)

        resolve_series_schema = cls(
            bucket_seconds=bucket_seconds,
            buckets=buckets,
        )

        resolve_series_schema.additional_properties = d
        return resolve_series_schema

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
