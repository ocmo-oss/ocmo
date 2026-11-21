from typing import Any, Dict, Type, TypeVar, Union, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="ChangeRequestAnchorSchema")


@_attrs_define
class ChangeRequestAnchorSchema:
    """
    Attributes:
        start_line (int): 1-based start line in CR content
        end_line (Union[None, Unset, int]): 1-based end line (inclusive); defaults to start_line when omitted
    """

    start_line: int
    end_line: Union[None, Unset, int] = UNSET

    def to_dict(self) -> Dict[str, Any]:
        start_line = self.start_line

        end_line: Union[None, Unset, int]
        if isinstance(self.end_line, Unset):
            end_line = UNSET
        else:
            end_line = self.end_line

        field_dict: Dict[str, Any] = {}
        field_dict.update(
            {
                "start_line": start_line,
            }
        )
        if end_line is not UNSET:
            field_dict["end_line"] = end_line

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        start_line = d.pop("start_line")

        def _parse_end_line(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        end_line = _parse_end_line(d.pop("end_line", UNSET))

        change_request_anchor_schema = cls(
            start_line=start_line,
            end_line=end_line,
        )

        return change_request_anchor_schema
