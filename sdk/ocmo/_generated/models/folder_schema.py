import datetime
from typing import Any, Dict, List, Literal, Type, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="FolderSchema")


@_attrs_define
class FolderSchema:
    """
    Attributes:
        name (str): Leaf segment name
        path (str): Full path within the namespace
        node_type (Literal['folder']):
        author (str): Last author identifier
        description (str): Markdown description
        created_at (datetime.datetime): Creation timestamp
    """

    name: str
    path: str
    node_type: Literal["folder"]
    author: str
    description: str
    created_at: datetime.datetime
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name = self.name

        path = self.path

        node_type = self.node_type

        author = self.author

        description = self.description

        created_at = self.created_at.isoformat()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "path": path,
                "node_type": node_type,
                "author": author,
                "description": description,
                "created_at": created_at,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        name = d.pop("name")

        path = d.pop("path")

        node_type = cast(Literal["folder"], d.pop("node_type"))
        if node_type != "folder":
            raise ValueError(f"node_type must match const 'folder', got '{node_type}'")

        author = d.pop("author")

        description = d.pop("description")

        created_at = isoparse(d.pop("created_at"))

        folder_schema = cls(
            name=name,
            path=path,
            node_type=node_type,
            author=author,
            description=description,
            created_at=created_at,
        )

        folder_schema.additional_properties = d
        return folder_schema

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
