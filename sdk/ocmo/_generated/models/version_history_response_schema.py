from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.config_schema import ConfigSchema
    from ..models.secret_schema import SecretSchema
    from ..models.template_schema import TemplateSchema
    from ..models.version_summary_schema import VersionSummarySchema


T = TypeVar("T", bound="VersionHistoryResponseSchema")


@_attrs_define
class VersionHistoryResponseSchema:
    """All versions of a config, template, or secret (newest first).

    Attributes:
        item (Union['ConfigSchema', 'SecretSchema', 'TemplateSchema']): Tree item metadata and tag map
        versions (List['VersionSummarySchema']): Version history entries without document content
        versions_count (int): Total number of versions for this item (before pagination)
    """

    item: Union["ConfigSchema", "SecretSchema", "TemplateSchema"]
    versions: List["VersionSummarySchema"]
    versions_count: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        from ..models.config_schema import ConfigSchema
        from ..models.template_schema import TemplateSchema

        item: Dict[str, Any]
        if isinstance(self.item, ConfigSchema):
            item = self.item.to_dict()
        elif isinstance(self.item, TemplateSchema):
            item = self.item.to_dict()
        else:
            item = self.item.to_dict()

        versions = []
        for versions_item_data in self.versions:
            versions_item = versions_item_data.to_dict()
            versions.append(versions_item)

        versions_count = self.versions_count

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "item": item,
                "versions": versions,
                "versions_count": versions_count,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.config_schema import ConfigSchema
        from ..models.secret_schema import SecretSchema
        from ..models.template_schema import TemplateSchema
        from ..models.version_summary_schema import VersionSummarySchema

        d = src_dict.copy()

        def _parse_item(data: object) -> Union["ConfigSchema", "SecretSchema", "TemplateSchema"]:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                item_type_0 = ConfigSchema.from_dict(data)

                return item_type_0
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                item_type_1 = TemplateSchema.from_dict(data)

                return item_type_1
            except:  # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            item_type_2 = SecretSchema.from_dict(data)

            return item_type_2

        item = _parse_item(d.pop("item"))

        versions = []
        _versions = d.pop("versions")
        for versions_item_data in _versions:
            versions_item = VersionSummarySchema.from_dict(versions_item_data)

            versions.append(versions_item)

        versions_count = d.pop("versions_count")

        version_history_response_schema = cls(
            item=item,
            versions=versions,
            versions_count=versions_count,
        )

        version_history_response_schema.additional_properties = d
        return version_history_response_schema

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
