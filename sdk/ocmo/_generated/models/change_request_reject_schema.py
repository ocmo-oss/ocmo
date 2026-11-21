from typing import Any, Dict, Type, TypeVar, Union

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="ChangeRequestRejectSchema")


@_attrs_define
class ChangeRequestRejectSchema:
    """
    Attributes:
        reason (Union[Unset, str]):  Default: ''.
    """

    reason: Union[Unset, str] = ""

    def to_dict(self) -> Dict[str, Any]:
        reason = self.reason

        field_dict: Dict[str, Any] = {}
        field_dict.update({})
        if reason is not UNSET:
            field_dict["reason"] = reason

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        reason = d.pop("reason", UNSET)

        change_request_reject_schema = cls(
            reason=reason,
        )

        return change_request_reject_schema
