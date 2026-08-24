from typing import TYPE_CHECKING, Any, Dict, List, Literal, Type, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.template_schema_extended_tags import TemplateSchemaExtendedTags
    from ..models.version_schema import VersionSchema


T = TypeVar("T", bound="TemplateSchemaExtended")


@_attrs_define
class TemplateSchemaExtended:
    """
    Attributes:
        name (str): Leaf segment name
        path (str): Full path within the namespace
        node_type (Literal['template']):
        author (str): Last author identifier
        description (str): Markdown description
        tags (TemplateSchemaExtendedTags):
        version_data (VersionSchema):
    """

    name: str
    path: str
    node_type: Literal["template"]
    author: str
    description: str
    tags: "TemplateSchemaExtendedTags"
    version_data: "VersionSchema"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name = self.name

        path = self.path

        node_type = self.node_type

        author = self.author

        description = self.description

        tags = self.tags.to_dict()

        version_data = self.version_data.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "path": path,
                "node_type": node_type,
                "author": author,
                "description": description,
                "tags": tags,
                "version_data": version_data,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.template_schema_extended_tags import TemplateSchemaExtendedTags
        from ..models.version_schema import VersionSchema

        d = src_dict.copy()
        name = d.pop("name")

        path = d.pop("path")

        node_type = cast(Literal["template"], d.pop("node_type"))
        if node_type != "template":
            raise ValueError(f"node_type must match const 'template', got '{node_type}'")

        author = d.pop("author")

        description = d.pop("description")

        tags = TemplateSchemaExtendedTags.from_dict(d.pop("tags"))

        version_data = VersionSchema.from_dict(d.pop("version_data"))

        template_schema_extended = cls(
            name=name,
            path=path,
            node_type=node_type,
            author=author,
            description=description,
            tags=tags,
            version_data=version_data,
        )

        template_schema_extended.additional_properties = d
        return template_schema_extended

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
