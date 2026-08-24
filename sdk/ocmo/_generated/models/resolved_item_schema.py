from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.resolved_item_schema_trace import ResolvedItemSchemaTrace


T = TypeVar("T", bound="ResolvedItemSchema")


@_attrs_define
class ResolvedItemSchema:
    """One resolved output document.

    Mirrors the design's resolve response item: `url` is the short-lived
    signed download URL for this artifact; the resolved bytes are NEVER
    returned inline.

        Attributes:
            name (str):
            version (int):
            format_ (str):
            url (Union[None, Unset, str]):
            checksum (Union[None, Unset, str]):
            trace (Union[Unset, ResolvedItemSchemaTrace]):
    """

    name: str
    version: int
    format_: str
    url: Union[None, Unset, str] = UNSET
    checksum: Union[None, Unset, str] = UNSET
    trace: Union[Unset, "ResolvedItemSchemaTrace"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        name = self.name

        version = self.version

        format_ = self.format_

        url: Union[None, Unset, str]
        if isinstance(self.url, Unset):
            url = UNSET
        else:
            url = self.url

        checksum: Union[None, Unset, str]
        if isinstance(self.checksum, Unset):
            checksum = UNSET
        else:
            checksum = self.checksum

        trace: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.trace, Unset):
            trace = self.trace.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "version": version,
                "format": format_,
            }
        )
        if url is not UNSET:
            field_dict["url"] = url
        if checksum is not UNSET:
            field_dict["checksum"] = checksum
        if trace is not UNSET:
            field_dict["trace"] = trace

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.resolved_item_schema_trace import ResolvedItemSchemaTrace

        d = src_dict.copy()
        name = d.pop("name")

        version = d.pop("version")

        format_ = d.pop("format")

        def _parse_url(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        url = _parse_url(d.pop("url", UNSET))

        def _parse_checksum(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        checksum = _parse_checksum(d.pop("checksum", UNSET))

        _trace = d.pop("trace", UNSET)
        trace: Union[Unset, ResolvedItemSchemaTrace]
        if isinstance(_trace, Unset):
            trace = UNSET
        else:
            trace = ResolvedItemSchemaTrace.from_dict(_trace)

        resolved_item_schema = cls(
            name=name,
            version=version,
            format_=format_,
            url=url,
            checksum=checksum,
            trace=trace,
        )

        resolved_item_schema.additional_properties = d
        return resolved_item_schema

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
