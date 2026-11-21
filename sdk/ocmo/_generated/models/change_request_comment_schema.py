import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.change_request_anchor_schema import ChangeRequestAnchorSchema


T = TypeVar("T", bound="ChangeRequestCommentSchema")


@_attrs_define
class ChangeRequestCommentSchema:
    """
    Attributes:
        id (int):
        author (str):
        body (str):
        created_at (datetime.datetime):
        anchor (Union['ChangeRequestAnchorSchema', None, Unset]):
    """

    id: int
    author: str
    body: str
    created_at: datetime.datetime
    anchor: Union["ChangeRequestAnchorSchema", None, Unset] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        from ..models.change_request_anchor_schema import ChangeRequestAnchorSchema

        id = self.id

        author = self.author

        body = self.body

        created_at = self.created_at.isoformat()

        anchor: Union[Dict[str, Any], None, Unset]
        if isinstance(self.anchor, Unset):
            anchor = UNSET
        elif isinstance(self.anchor, ChangeRequestAnchorSchema):
            anchor = self.anchor.to_dict()
        else:
            anchor = self.anchor

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "author": author,
                "body": body,
                "created_at": created_at,
            }
        )
        if anchor is not UNSET:
            field_dict["anchor"] = anchor

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.change_request_anchor_schema import ChangeRequestAnchorSchema

        d = src_dict.copy()
        id = d.pop("id")

        author = d.pop("author")

        body = d.pop("body")

        created_at = isoparse(d.pop("created_at"))

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

        change_request_comment_schema = cls(
            id=id,
            author=author,
            body=body,
            created_at=created_at,
            anchor=anchor,
        )

        change_request_comment_schema.additional_properties = d
        return change_request_comment_schema

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
