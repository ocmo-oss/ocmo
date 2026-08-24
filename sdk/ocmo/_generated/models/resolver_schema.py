import datetime
from typing import Any, Dict, List, Literal, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="ResolverSchema")


@_attrs_define
class ResolverSchema:
    """
    Attributes:
        name (str): Leaf segment name
        path (str): Full path within the namespace
        node_type (Literal['resolver']):
        author (str): Last author identifier
        description (str): Markdown description
        created_at (datetime.datetime): Creation timestamp
        configuration (Union[None, Unset, str]):
        token1 (Union[None, Unset, str]):
        token1_last_used (Union[None, Unset, datetime.datetime]):
        token2 (Union[None, Unset, str]):
        token2_last_used (Union[None, Unset, datetime.datetime]):
    """

    name: str
    path: str
    node_type: Literal["resolver"]
    author: str
    description: str
    created_at: datetime.datetime
    configuration: Union[None, Unset, str] = UNSET
    token1: Union[None, Unset, str] = UNSET
    token1_last_used: Union[None, Unset, datetime.datetime] = UNSET
    token2: Union[None, Unset, str] = UNSET
    token2_last_used: Union[None, Unset, datetime.datetime] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name = self.name

        path = self.path

        node_type = self.node_type

        author = self.author

        description = self.description

        created_at = self.created_at.isoformat()

        configuration: Union[None, Unset, str]
        if isinstance(self.configuration, Unset):
            configuration = UNSET
        else:
            configuration = self.configuration

        token1: Union[None, Unset, str]
        if isinstance(self.token1, Unset):
            token1 = UNSET
        else:
            token1 = self.token1

        token1_last_used: Union[None, Unset, str]
        if isinstance(self.token1_last_used, Unset):
            token1_last_used = UNSET
        elif isinstance(self.token1_last_used, datetime.datetime):
            token1_last_used = self.token1_last_used.isoformat()
        else:
            token1_last_used = self.token1_last_used

        token2: Union[None, Unset, str]
        if isinstance(self.token2, Unset):
            token2 = UNSET
        else:
            token2 = self.token2

        token2_last_used: Union[None, Unset, str]
        if isinstance(self.token2_last_used, Unset):
            token2_last_used = UNSET
        elif isinstance(self.token2_last_used, datetime.datetime):
            token2_last_used = self.token2_last_used.isoformat()
        else:
            token2_last_used = self.token2_last_used

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
        if configuration is not UNSET:
            field_dict["configuration"] = configuration
        if token1 is not UNSET:
            field_dict["token1"] = token1
        if token1_last_used is not UNSET:
            field_dict["token1_last_used"] = token1_last_used
        if token2 is not UNSET:
            field_dict["token2"] = token2
        if token2_last_used is not UNSET:
            field_dict["token2_last_used"] = token2_last_used

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        name = d.pop("name")

        path = d.pop("path")

        node_type = cast(Literal["resolver"], d.pop("node_type"))
        if node_type != "resolver":
            raise ValueError(f"node_type must match const 'resolver', got '{node_type}'")

        author = d.pop("author")

        description = d.pop("description")

        created_at = isoparse(d.pop("created_at"))

        def _parse_configuration(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        configuration = _parse_configuration(d.pop("configuration", UNSET))

        def _parse_token1(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        token1 = _parse_token1(d.pop("token1", UNSET))

        def _parse_token1_last_used(data: object) -> Union[None, Unset, datetime.datetime]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                token1_last_used_type_0 = isoparse(data)

                return token1_last_used_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        token1_last_used = _parse_token1_last_used(d.pop("token1_last_used", UNSET))

        def _parse_token2(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        token2 = _parse_token2(d.pop("token2", UNSET))

        def _parse_token2_last_used(data: object) -> Union[None, Unset, datetime.datetime]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                token2_last_used_type_0 = isoparse(data)

                return token2_last_used_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        token2_last_used = _parse_token2_last_used(d.pop("token2_last_used", UNSET))

        resolver_schema = cls(
            name=name,
            path=path,
            node_type=node_type,
            author=author,
            description=description,
            created_at=created_at,
            configuration=configuration,
            token1=token1,
            token1_last_used=token1_last_used,
            token2=token2,
            token2_last_used=token2_last_used,
        )

        resolver_schema.additional_properties = d
        return resolver_schema

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
