from typing import Any, Dict, List, Type, TypeVar, Union, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ErrorSchema")


@_attrs_define
class ErrorSchema:
    """
    Attributes:
        error (Union[List[Any], str]):
        audit_event_id (Union[None, UUID, Unset]): Audit log event ID when the failure was recorded server-side
    """

    error: Union[List[Any], str]
    audit_event_id: Union[None, UUID, Unset] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        error: Union[List[Any], str]
        if isinstance(self.error, list):
            error = self.error

        else:
            error = self.error

        audit_event_id: Union[None, Unset, str]
        if isinstance(self.audit_event_id, Unset):
            audit_event_id = UNSET
        elif isinstance(self.audit_event_id, UUID):
            audit_event_id = str(self.audit_event_id)
        else:
            audit_event_id = self.audit_event_id

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "error": error,
            }
        )
        if audit_event_id is not UNSET:
            field_dict["audit_event_id"] = audit_event_id

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()

        def _parse_error(data: object) -> Union[List[Any], str]:
            try:
                if not isinstance(data, list):
                    raise TypeError()
                error_type_1 = cast(List[Any], data)

                return error_type_1
            except:  # noqa: E722
                pass
            return cast(Union[List[Any], str], data)

        error = _parse_error(d.pop("error"))

        def _parse_audit_event_id(data: object) -> Union[None, UUID, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                audit_event_id_type_0 = UUID(data)

                return audit_event_id_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, UUID, Unset], data)

        audit_event_id = _parse_audit_event_id(d.pop("audit_event_id", UNSET))

        error_schema = cls(
            error=error,
            audit_event_id=audit_event_id,
        )

        error_schema.additional_properties = d
        return error_schema

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
