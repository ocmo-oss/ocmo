import datetime
from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="LockSchema")


@_attrs_define
class LockSchema:
    """Active subtree lock at a tree path.

    Attributes:
        path (str): Locked path (covers this path and descendants)
        reason (str): Freeze rationale
        created_at (datetime.datetime):
        updated_at (datetime.datetime):
        expires_at (Union[None, Unset, datetime.datetime]): UTC expiry; null means until explicitly removed
        locked_by (Union[Unset, str]): Identity that created the lock Default: ''.
    """

    path: str
    reason: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    expires_at: Union[None, Unset, datetime.datetime] = UNSET
    locked_by: Union[Unset, str] = ""
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        path = self.path

        reason = self.reason

        created_at = self.created_at.isoformat()

        updated_at = self.updated_at.isoformat()

        expires_at: Union[None, Unset, str]
        if isinstance(self.expires_at, Unset):
            expires_at = UNSET
        elif isinstance(self.expires_at, datetime.datetime):
            expires_at = self.expires_at.isoformat()
        else:
            expires_at = self.expires_at

        locked_by = self.locked_by

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "path": path,
                "reason": reason,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
        if expires_at is not UNSET:
            field_dict["expires_at"] = expires_at
        if locked_by is not UNSET:
            field_dict["locked_by"] = locked_by

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        path = d.pop("path")

        reason = d.pop("reason")

        created_at = isoparse(d.pop("created_at"))

        updated_at = isoparse(d.pop("updated_at"))

        def _parse_expires_at(data: object) -> Union[None, Unset, datetime.datetime]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                expires_at_type_0 = isoparse(data)

                return expires_at_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        expires_at = _parse_expires_at(d.pop("expires_at", UNSET))

        locked_by = d.pop("locked_by", UNSET)

        lock_schema = cls(
            path=path,
            reason=reason,
            created_at=created_at,
            updated_at=updated_at,
            expires_at=expires_at,
            locked_by=locked_by,
        )

        lock_schema.additional_properties = d
        return lock_schema

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
