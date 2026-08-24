from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="NamespacePatchSchema")


@_attrs_define
class NamespacePatchSchema:
    """
    Attributes:
        name (Union[None, Unset, str]): New namespace name
        description (Union[None, Unset, str]): Updated description. Markdown supported
        permissions_tag (Union[None, Unset, str]):
        webhooks_tag (Union[None, Unset, str]):
        git_sync_tag (Union[None, Unset, str]):
    """

    name: Union[None, Unset, str] = UNSET
    description: Union[None, Unset, str] = UNSET
    permissions_tag: Union[None, Unset, str] = UNSET
    webhooks_tag: Union[None, Unset, str] = UNSET
    git_sync_tag: Union[None, Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name: Union[None, Unset, str]
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        description: Union[None, Unset, str]
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        permissions_tag: Union[None, Unset, str]
        if isinstance(self.permissions_tag, Unset):
            permissions_tag = UNSET
        else:
            permissions_tag = self.permissions_tag

        webhooks_tag: Union[None, Unset, str]
        if isinstance(self.webhooks_tag, Unset):
            webhooks_tag = UNSET
        else:
            webhooks_tag = self.webhooks_tag

        git_sync_tag: Union[None, Unset, str]
        if isinstance(self.git_sync_tag, Unset):
            git_sync_tag = UNSET
        else:
            git_sync_tag = self.git_sync_tag

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if description is not UNSET:
            field_dict["description"] = description
        if permissions_tag is not UNSET:
            field_dict["permissions_tag"] = permissions_tag
        if webhooks_tag is not UNSET:
            field_dict["webhooks_tag"] = webhooks_tag
        if git_sync_tag is not UNSET:
            field_dict["git_sync_tag"] = git_sync_tag

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()

        def _parse_name(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        name = _parse_name(d.pop("name", UNSET))

        def _parse_description(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_permissions_tag(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        permissions_tag = _parse_permissions_tag(d.pop("permissions_tag", UNSET))

        def _parse_webhooks_tag(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        webhooks_tag = _parse_webhooks_tag(d.pop("webhooks_tag", UNSET))

        def _parse_git_sync_tag(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        git_sync_tag = _parse_git_sync_tag(d.pop("git_sync_tag", UNSET))

        namespace_patch_schema = cls(
            name=name,
            description=description,
            permissions_tag=permissions_tag,
            webhooks_tag=webhooks_tag,
            git_sync_tag=git_sync_tag,
        )

        namespace_patch_schema.additional_properties = d
        return namespace_patch_schema

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
