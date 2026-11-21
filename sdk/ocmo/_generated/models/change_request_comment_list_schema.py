from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.change_request_comment_schema import ChangeRequestCommentSchema


T = TypeVar("T", bound="ChangeRequestCommentListSchema")


@_attrs_define
class ChangeRequestCommentListSchema:
    """
    Attributes:
        items (List['ChangeRequestCommentSchema']):
        total (int):
        limit (int):
        offset (int):
    """

    items: List["ChangeRequestCommentSchema"]
    total: int
    limit: int
    offset: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        items = []
        for items_item_data in self.items:
            items_item = items_item_data.to_dict()
            items.append(items_item)

        total = self.total

        limit = self.limit

        offset = self.offset

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "items": items,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.change_request_comment_schema import ChangeRequestCommentSchema

        d = src_dict.copy()
        items = []
        _items = d.pop("items")
        for items_item_data in _items:
            items_item = ChangeRequestCommentSchema.from_dict(items_item_data)

            items.append(items_item)

        total = d.pop("total")

        limit = d.pop("limit")

        offset = d.pop("offset")

        change_request_comment_list_schema = cls(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

        change_request_comment_list_schema.additional_properties = d
        return change_request_comment_list_schema

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
