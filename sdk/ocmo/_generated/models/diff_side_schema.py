from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="DiffSideSchema")


@_attrs_define
class DiffSideSchema:
    """One side of a tree item diff (path, resolved version, optional content).

    Attributes:
        path (str): Tree path for this side
        node_type (str): Item type discriminator
        requested (str): Version or tag as requested (?from= / ?to=)
        version (int): Resolved immutable version number
        data (Union[None, Unset, str]): Version body (config/template text or decrypted secret); omitted when decryption
            is required
    """

    path: str
    node_type: str
    requested: str
    version: int
    data: Union[None, Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        path = self.path

        node_type = self.node_type

        requested = self.requested

        version = self.version

        data: Union[None, Unset, str]
        if isinstance(self.data, Unset):
            data = UNSET
        else:
            data = self.data

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "path": path,
                "node_type": node_type,
                "requested": requested,
                "version": version,
            }
        )
        if data is not UNSET:
            field_dict["data"] = data

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        path = d.pop("path")

        node_type = d.pop("node_type")

        requested = d.pop("requested")

        version = d.pop("version")

        def _parse_data(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        data = _parse_data(d.pop("data", UNSET))

        diff_side_schema = cls(
            path=path,
            node_type=node_type,
            requested=requested,
            version=version,
            data=data,
        )

        diff_side_schema.additional_properties = d
        return diff_side_schema

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
