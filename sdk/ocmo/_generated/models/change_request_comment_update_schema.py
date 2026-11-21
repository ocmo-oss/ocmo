from typing import Any, Dict, Type, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="ChangeRequestCommentUpdateSchema")


@_attrs_define
class ChangeRequestCommentUpdateSchema:
    """
    Attributes:
        body (str):
    """

    body: str

    def to_dict(self) -> Dict[str, Any]:
        body = self.body

        field_dict: Dict[str, Any] = {}
        field_dict.update(
            {
                "body": body,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        body = d.pop("body")

        change_request_comment_update_schema = cls(
            body=body,
        )

        return change_request_comment_update_schema
