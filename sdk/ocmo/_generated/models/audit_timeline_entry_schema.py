import datetime
from typing import Any, Dict, List, Type, TypeVar, Union, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="AuditTimelineEntrySchema")


@_attrs_define
class AuditTimelineEntrySchema:
    """
    Attributes:
        id (UUID):
        occurred_at (datetime.datetime):
        message (str): User-friendly timeline note for this event
        auth_id (str):
        auth_type (str):
        event_kind (str):
        operation (Union[None, Unset, str]):
        object_type (Union[None, Unset, str]):
        object_id (Union[None, Unset, str]):
        object_version (Union[None, Unset, int]):
        subresource_type (Union[None, Unset, str]):
        subresource (Union[None, Unset, str]):
        auth_email (Union[None, Unset, str]):
        permission_ok (Union[None, Unset, bool]):
    """

    id: UUID
    occurred_at: datetime.datetime
    message: str
    auth_id: str
    auth_type: str
    event_kind: str
    operation: Union[None, Unset, str] = UNSET
    object_type: Union[None, Unset, str] = UNSET
    object_id: Union[None, Unset, str] = UNSET
    object_version: Union[None, Unset, int] = UNSET
    subresource_type: Union[None, Unset, str] = UNSET
    subresource: Union[None, Unset, str] = UNSET
    auth_email: Union[None, Unset, str] = UNSET
    permission_ok: Union[None, Unset, bool] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = str(self.id)

        occurred_at = self.occurred_at.isoformat()

        message = self.message

        auth_id = self.auth_id

        auth_type = self.auth_type

        event_kind = self.event_kind

        operation: Union[None, Unset, str]
        if isinstance(self.operation, Unset):
            operation = UNSET
        else:
            operation = self.operation

        object_type: Union[None, Unset, str]
        if isinstance(self.object_type, Unset):
            object_type = UNSET
        else:
            object_type = self.object_type

        object_id: Union[None, Unset, str]
        if isinstance(self.object_id, Unset):
            object_id = UNSET
        else:
            object_id = self.object_id

        object_version: Union[None, Unset, int]
        if isinstance(self.object_version, Unset):
            object_version = UNSET
        else:
            object_version = self.object_version

        subresource_type: Union[None, Unset, str]
        if isinstance(self.subresource_type, Unset):
            subresource_type = UNSET
        else:
            subresource_type = self.subresource_type

        subresource: Union[None, Unset, str]
        if isinstance(self.subresource, Unset):
            subresource = UNSET
        else:
            subresource = self.subresource

        auth_email: Union[None, Unset, str]
        if isinstance(self.auth_email, Unset):
            auth_email = UNSET
        else:
            auth_email = self.auth_email

        permission_ok: Union[None, Unset, bool]
        if isinstance(self.permission_ok, Unset):
            permission_ok = UNSET
        else:
            permission_ok = self.permission_ok

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "occurred_at": occurred_at,
                "message": message,
                "auth_id": auth_id,
                "auth_type": auth_type,
                "event_kind": event_kind,
            }
        )
        if operation is not UNSET:
            field_dict["operation"] = operation
        if object_type is not UNSET:
            field_dict["object_type"] = object_type
        if object_id is not UNSET:
            field_dict["object_id"] = object_id
        if object_version is not UNSET:
            field_dict["object_version"] = object_version
        if subresource_type is not UNSET:
            field_dict["subresource_type"] = subresource_type
        if subresource is not UNSET:
            field_dict["subresource"] = subresource
        if auth_email is not UNSET:
            field_dict["auth_email"] = auth_email
        if permission_ok is not UNSET:
            field_dict["permission_ok"] = permission_ok

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        id = UUID(d.pop("id"))

        occurred_at = isoparse(d.pop("occurred_at"))

        message = d.pop("message")

        auth_id = d.pop("auth_id")

        auth_type = d.pop("auth_type")

        event_kind = d.pop("event_kind")

        def _parse_operation(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        operation = _parse_operation(d.pop("operation", UNSET))

        def _parse_object_type(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        object_type = _parse_object_type(d.pop("object_type", UNSET))

        def _parse_object_id(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        object_id = _parse_object_id(d.pop("object_id", UNSET))

        def _parse_object_version(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        object_version = _parse_object_version(d.pop("object_version", UNSET))

        def _parse_subresource_type(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        subresource_type = _parse_subresource_type(d.pop("subresource_type", UNSET))

        def _parse_subresource(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        subresource = _parse_subresource(d.pop("subresource", UNSET))

        def _parse_auth_email(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        auth_email = _parse_auth_email(d.pop("auth_email", UNSET))

        def _parse_permission_ok(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        permission_ok = _parse_permission_ok(d.pop("permission_ok", UNSET))

        audit_timeline_entry_schema = cls(
            id=id,
            occurred_at=occurred_at,
            message=message,
            auth_id=auth_id,
            auth_type=auth_type,
            event_kind=event_kind,
            operation=operation,
            object_type=object_type,
            object_id=object_id,
            object_version=object_version,
            subresource_type=subresource_type,
            subresource=subresource,
            auth_email=auth_email,
            permission_ok=permission_ok,
        )

        audit_timeline_entry_schema.additional_properties = d
        return audit_timeline_entry_schema

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
