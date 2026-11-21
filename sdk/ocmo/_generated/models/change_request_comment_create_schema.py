from typing import TYPE_CHECKING, Any, Dict, Type, TypeVar, Union, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.change_request_anchor_schema import ChangeRequestAnchorSchema


T = TypeVar("T", bound="ChangeRequestCommentCreateSchema")


@_attrs_define
class ChangeRequestCommentCreateSchema:
    """
    Attributes:
        body (str):
        anchor (Union['ChangeRequestAnchorSchema', None, Unset]):
    """

    body: str
    anchor: Union["ChangeRequestAnchorSchema", None, Unset] = UNSET

    def to_dict(self) -> Dict[str, Any]:
        from ..models.change_request_anchor_schema import ChangeRequestAnchorSchema

        body = self.body

        anchor: Union[Dict[str, Any], None, Unset]
        if isinstance(self.anchor, Unset):
            anchor = UNSET
        elif isinstance(self.anchor, ChangeRequestAnchorSchema):
            anchor = self.anchor.to_dict()
        else:
            anchor = self.anchor

        field_dict: Dict[str, Any] = {}
        field_dict.update(
            {
                "body": body,
            }
        )
        if anchor is not UNSET:
            field_dict["anchor"] = anchor

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.change_request_anchor_schema import ChangeRequestAnchorSchema

        d = src_dict.copy()
        body = d.pop("body")

        def _parse_anchor(data: object) -> Union["ChangeRequestAnchorSchema", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                anchor_type_0 = ChangeRequestAnchorSchema.from_dict(data)

                return anchor_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ChangeRequestAnchorSchema", None, Unset], data)

        anchor = _parse_anchor(d.pop("anchor", UNSET))

        change_request_comment_create_schema = cls(
            body=body,
            anchor=anchor,
        )

        return change_request_comment_create_schema
