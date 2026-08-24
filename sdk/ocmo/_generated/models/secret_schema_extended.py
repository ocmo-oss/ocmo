from typing import TYPE_CHECKING, Any, Dict, List, Literal, Type, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.secret_schema_extended_tags import SecretSchemaExtendedTags
    from ..models.secret_version_schema import SecretVersionSchema


T = TypeVar("T", bound="SecretSchemaExtended")


@_attrs_define
class SecretSchemaExtended:
    """
    Attributes:
        name (str): Leaf segment name
        path (str): Full path within the namespace
        node_type (Literal['secret']):
        author (str): Last author identifier
        description (str): Markdown description
        tags (SecretSchemaExtendedTags):
        version_data (SecretVersionSchema):
    """

    name: str
    path: str
    node_type: Literal["secret"]
    author: str
    description: str
    tags: "SecretSchemaExtendedTags"
    version_data: "SecretVersionSchema"
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
        from ..models.secret_schema_extended_tags import SecretSchemaExtendedTags
        from ..models.secret_version_schema import SecretVersionSchema

        d = src_dict.copy()
        name = d.pop("name")

        path = d.pop("path")

        node_type = cast(Literal["secret"], d.pop("node_type"))
        if node_type != "secret":
            raise ValueError(f"node_type must match const 'secret', got '{node_type}'")

        author = d.pop("author")

        description = d.pop("description")

        tags = SecretSchemaExtendedTags.from_dict(d.pop("tags"))

        version_data = SecretVersionSchema.from_dict(d.pop("version_data"))

        secret_schema_extended = cls(
            name=name,
            path=path,
            node_type=node_type,
            author=author,
            description=description,
            tags=tags,
            version_data=version_data,
        )

        secret_schema_extended.additional_properties = d
        return secret_schema_extended

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
