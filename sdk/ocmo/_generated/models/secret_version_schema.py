import datetime
from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="SecretVersionSchema")


@_attrs_define
class SecretVersionSchema:
    """
    Attributes:
        version (Union[int, str]):
        tags (List[str]):
        updater (str):
        updated_at (datetime.datetime):
        deleted_at (Union[None, datetime.datetime]):
        data (Union[None, Unset, str]):
    """

    version: Union[int, str]
    tags: List[str]
    updater: str
    updated_at: datetime.datetime
    deleted_at: Union[None, datetime.datetime]
    data: Union[None, Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        version: Union[int, str]
        version = self.version

        tags = self.tags

        updater = self.updater

        updated_at = self.updated_at.isoformat()

        deleted_at: Union[None, str]
        if isinstance(self.deleted_at, datetime.datetime):
            deleted_at = self.deleted_at.isoformat()
        else:
            deleted_at = self.deleted_at

        data: Union[None, Unset, str]
        if isinstance(self.data, Unset):
            data = UNSET
        else:
            data = self.data

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "version": version,
                "tags": tags,
                "updater": updater,
                "updated_at": updated_at,
                "deleted_at": deleted_at,
            }
        )
        if data is not UNSET:
            field_dict["data"] = data

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()

        def _parse_version(data: object) -> Union[int, str]:
            return cast(Union[int, str], data)

        version = _parse_version(d.pop("version"))

        tags = cast(List[str], d.pop("tags"))

        updater = d.pop("updater")

        updated_at = isoparse(d.pop("updated_at"))

        def _parse_deleted_at(data: object) -> Union[None, datetime.datetime]:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                deleted_at_type_0 = isoparse(data)

                return deleted_at_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, datetime.datetime], data)

        deleted_at = _parse_deleted_at(d.pop("deleted_at"))

        def _parse_data(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        data = _parse_data(d.pop("data", UNSET))

        secret_version_schema = cls(
            version=version,
            tags=tags,
            updater=updater,
            updated_at=updated_at,
            deleted_at=deleted_at,
            data=data,
        )

        secret_version_schema.additional_properties = d
        return secret_version_schema

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
