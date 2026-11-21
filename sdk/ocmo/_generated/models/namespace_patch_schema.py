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
        change_requests_enabled (Union[None, Unset, bool]):
        change_requests_required_approvals (Union[None, Unset, int]):
        change_requests_auto_reject_on_new_version (Union[None, Unset, bool]):
        change_requests_max_open_per_user_per_resource (Union[None, Unset, int]):
        change_requests_reset_approvals_on_change (Union[None, Unset, bool]):
    """

    name: Union[None, Unset, str] = UNSET
    description: Union[None, Unset, str] = UNSET
    permissions_tag: Union[None, Unset, str] = UNSET
    webhooks_tag: Union[None, Unset, str] = UNSET
    git_sync_tag: Union[None, Unset, str] = UNSET
    change_requests_enabled: Union[None, Unset, bool] = UNSET
    change_requests_required_approvals: Union[None, Unset, int] = UNSET
    change_requests_auto_reject_on_new_version: Union[None, Unset, bool] = UNSET
    change_requests_max_open_per_user_per_resource: Union[None, Unset, int] = UNSET
    change_requests_reset_approvals_on_change: Union[None, Unset, bool] = UNSET
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

        change_requests_enabled: Union[None, Unset, bool]
        if isinstance(self.change_requests_enabled, Unset):
            change_requests_enabled = UNSET
        else:
            change_requests_enabled = self.change_requests_enabled

        change_requests_required_approvals: Union[None, Unset, int]
        if isinstance(self.change_requests_required_approvals, Unset):
            change_requests_required_approvals = UNSET
        else:
            change_requests_required_approvals = self.change_requests_required_approvals

        change_requests_auto_reject_on_new_version: Union[None, Unset, bool]
        if isinstance(self.change_requests_auto_reject_on_new_version, Unset):
            change_requests_auto_reject_on_new_version = UNSET
        else:
            change_requests_auto_reject_on_new_version = self.change_requests_auto_reject_on_new_version

        change_requests_max_open_per_user_per_resource: Union[None, Unset, int]
        if isinstance(self.change_requests_max_open_per_user_per_resource, Unset):
            change_requests_max_open_per_user_per_resource = UNSET
        else:
            change_requests_max_open_per_user_per_resource = self.change_requests_max_open_per_user_per_resource

        change_requests_reset_approvals_on_change: Union[None, Unset, bool]
        if isinstance(self.change_requests_reset_approvals_on_change, Unset):
            change_requests_reset_approvals_on_change = UNSET
        else:
            change_requests_reset_approvals_on_change = self.change_requests_reset_approvals_on_change

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
        if change_requests_enabled is not UNSET:
            field_dict["change_requests_enabled"] = change_requests_enabled
        if change_requests_required_approvals is not UNSET:
            field_dict["change_requests_required_approvals"] = change_requests_required_approvals
        if change_requests_auto_reject_on_new_version is not UNSET:
            field_dict["change_requests_auto_reject_on_new_version"] = change_requests_auto_reject_on_new_version
        if change_requests_max_open_per_user_per_resource is not UNSET:
            field_dict["change_requests_max_open_per_user_per_resource"] = (
                change_requests_max_open_per_user_per_resource
            )
        if change_requests_reset_approvals_on_change is not UNSET:
            field_dict["change_requests_reset_approvals_on_change"] = change_requests_reset_approvals_on_change

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

        def _parse_change_requests_enabled(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        change_requests_enabled = _parse_change_requests_enabled(d.pop("change_requests_enabled", UNSET))

        def _parse_change_requests_required_approvals(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        change_requests_required_approvals = _parse_change_requests_required_approvals(
            d.pop("change_requests_required_approvals", UNSET)
        )

        def _parse_change_requests_auto_reject_on_new_version(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        change_requests_auto_reject_on_new_version = _parse_change_requests_auto_reject_on_new_version(
            d.pop("change_requests_auto_reject_on_new_version", UNSET)
        )

        def _parse_change_requests_max_open_per_user_per_resource(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        change_requests_max_open_per_user_per_resource = _parse_change_requests_max_open_per_user_per_resource(
            d.pop("change_requests_max_open_per_user_per_resource", UNSET)
        )

        def _parse_change_requests_reset_approvals_on_change(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        change_requests_reset_approvals_on_change = _parse_change_requests_reset_approvals_on_change(
            d.pop("change_requests_reset_approvals_on_change", UNSET)
        )

        namespace_patch_schema = cls(
            name=name,
            description=description,
            permissions_tag=permissions_tag,
            webhooks_tag=webhooks_tag,
            git_sync_tag=git_sync_tag,
            change_requests_enabled=change_requests_enabled,
            change_requests_required_approvals=change_requests_required_approvals,
            change_requests_auto_reject_on_new_version=change_requests_auto_reject_on_new_version,
            change_requests_max_open_per_user_per_resource=change_requests_max_open_per_user_per_resource,
            change_requests_reset_approvals_on_change=change_requests_reset_approvals_on_change,
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
