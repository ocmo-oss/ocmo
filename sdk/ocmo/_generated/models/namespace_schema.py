import datetime
from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="NamespaceSchema")


@_attrs_define
class NamespaceSchema:
    """
    Attributes:
        name (str):
        description (str):
        permissions_tag (str):
        webhooks_tag (str):
        git_sync_tag (str):
        created_at (datetime.datetime):
        updated_at (datetime.datetime):
    """

    name: str
    description: str
    permissions_tag: str
    webhooks_tag: str
    git_sync_tag: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name = self.name

        description = self.description

        permissions_tag = self.permissions_tag

        webhooks_tag = self.webhooks_tag

        git_sync_tag = self.git_sync_tag

        created_at = self.created_at.isoformat()

        updated_at = self.updated_at.isoformat()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "description": description,
                "permissions_tag": permissions_tag,
                "webhooks_tag": webhooks_tag,
                "git_sync_tag": git_sync_tag,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        name = d.pop("name")

        description = d.pop("description")

        permissions_tag = d.pop("permissions_tag")

        webhooks_tag = d.pop("webhooks_tag")

        git_sync_tag = d.pop("git_sync_tag")

        created_at = isoparse(d.pop("created_at"))

        updated_at = isoparse(d.pop("updated_at"))

        namespace_schema = cls(
            name=name,
            description=description,
            permissions_tag=permissions_tag,
            webhooks_tag=webhooks_tag,
            git_sync_tag=git_sync_tag,
            created_at=created_at,
            updated_at=updated_at,
        )

        namespace_schema.additional_properties = d
        return namespace_schema

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
