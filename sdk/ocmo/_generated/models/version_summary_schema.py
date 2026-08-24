import datetime
from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="VersionSummarySchema")


@_attrs_define
class VersionSummarySchema:
    """One version row in a version history list (metadata only; no content).

    Attributes:
        version (int): Immutable version number
        tags (List[str]): Tag names pointing at this version (e.g. latest, stable, custom)
        updater (str): Identity that created this version
        updated_at (datetime.datetime): UTC timestamp when this version was created
        deleted_at (Union[None, Unset, datetime.datetime]): Set when this version was soft-deleted; content is cleared
    """

    version: int
    tags: List[str]
    updater: str
    updated_at: datetime.datetime
    deleted_at: Union[None, Unset, datetime.datetime] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        version = self.version

        tags = self.tags

        updater = self.updater

        updated_at = self.updated_at.isoformat()

        deleted_at: Union[None, Unset, str]
        if isinstance(self.deleted_at, Unset):
            deleted_at = UNSET
        elif isinstance(self.deleted_at, datetime.datetime):
            deleted_at = self.deleted_at.isoformat()
        else:
            deleted_at = self.deleted_at

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "version": version,
                "tags": tags,
                "updater": updater,
                "updated_at": updated_at,
            }
        )
        if deleted_at is not UNSET:
            field_dict["deleted_at"] = deleted_at

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        version = d.pop("version")

        tags = cast(List[str], d.pop("tags"))

        updater = d.pop("updater")

        updated_at = isoparse(d.pop("updated_at"))

        def _parse_deleted_at(data: object) -> Union[None, Unset, datetime.datetime]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                deleted_at_type_0 = isoparse(data)

                return deleted_at_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        deleted_at = _parse_deleted_at(d.pop("deleted_at", UNSET))

        version_summary_schema = cls(
            version=version,
            tags=tags,
            updater=updater,
            updated_at=updated_at,
            deleted_at=deleted_at,
        )

        version_summary_schema.additional_properties = d
        return version_summary_schema

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
