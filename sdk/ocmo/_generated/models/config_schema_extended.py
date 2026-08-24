from typing import TYPE_CHECKING, Any, Dict, List, Literal, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.config_schema_extended_tags import ConfigSchemaExtendedTags
    from ..models.propagation_result_schema import PropagationResultSchema
    from ..models.version_schema import VersionSchema


T = TypeVar("T", bound="ConfigSchemaExtended")


@_attrs_define
class ConfigSchemaExtended:
    """
    Attributes:
        name (str): Leaf segment name
        path (str): Full path within the namespace
        node_type (Literal['config']):
        author (str): Last author identifier
        description (str): Markdown description
        tags (ConfigSchemaExtendedTags):
        version_data (VersionSchema):
        propagation (Union['PropagationResultSchema', None, Unset]):
    """

    name: str
    path: str
    node_type: Literal["config"]
    author: str
    description: str
    tags: "ConfigSchemaExtendedTags"
    version_data: "VersionSchema"
    propagation: Union["PropagationResultSchema", None, Unset] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        from ..models.propagation_result_schema import PropagationResultSchema

        name = self.name

        path = self.path

        node_type = self.node_type

        author = self.author

        description = self.description

        tags = self.tags.to_dict()

        version_data = self.version_data.to_dict()

        propagation: Union[Dict[str, Any], None, Unset]
        if isinstance(self.propagation, Unset):
            propagation = UNSET
        elif isinstance(self.propagation, PropagationResultSchema):
            propagation = self.propagation.to_dict()
        else:
            propagation = self.propagation

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
        if propagation is not UNSET:
            field_dict["propagation"] = propagation

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.config_schema_extended_tags import ConfigSchemaExtendedTags
        from ..models.propagation_result_schema import PropagationResultSchema
        from ..models.version_schema import VersionSchema

        d = src_dict.copy()
        name = d.pop("name")

        path = d.pop("path")

        node_type = cast(Literal["config"], d.pop("node_type"))
        if node_type != "config":
            raise ValueError(f"node_type must match const 'config', got '{node_type}'")

        author = d.pop("author")

        description = d.pop("description")

        tags = ConfigSchemaExtendedTags.from_dict(d.pop("tags"))

        version_data = VersionSchema.from_dict(d.pop("version_data"))

        def _parse_propagation(data: object) -> Union["PropagationResultSchema", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                propagation_type_0 = PropagationResultSchema.from_dict(data)

                return propagation_type_0
            except:  # noqa: E722
                pass
            return cast(Union["PropagationResultSchema", None, Unset], data)

        propagation = _parse_propagation(d.pop("propagation", UNSET))

        config_schema_extended = cls(
            name=name,
            path=path,
            node_type=node_type,
            author=author,
            description=description,
            tags=tags,
            version_data=version_data,
            propagation=propagation,
        )

        config_schema_extended.additional_properties = d
        return config_schema_extended

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
