from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.tree_navigation_node_schema import TreeNavigationNodeSchema


T = TypeVar("T", bound="NavigationSchema")


@_attrs_define
class NavigationSchema:
    """
    Attributes:
        item (Union['TreeNavigationNodeSchema', None]):
        children (List['TreeNavigationNodeSchema']):
        children_count (int): Total number of child nodes (before pagination)
        breadcrumbs (List[str]):
        is_leaf (bool):
    """

    item: Union["TreeNavigationNodeSchema", None]
    children: List["TreeNavigationNodeSchema"]
    children_count: int
    breadcrumbs: List[str]
    is_leaf: bool
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        from ..models.tree_navigation_node_schema import TreeNavigationNodeSchema

        item: Union[Dict[str, Any], None]
        if isinstance(self.item, TreeNavigationNodeSchema):
            item = self.item.to_dict()
        else:
            item = self.item

        children = []
        for children_item_data in self.children:
            children_item = children_item_data.to_dict()
            children.append(children_item)

        children_count = self.children_count

        breadcrumbs = self.breadcrumbs

        is_leaf = self.is_leaf

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "item": item,
                "children": children,
                "children_count": children_count,
                "breadcrumbs": breadcrumbs,
                "is_leaf": is_leaf,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.tree_navigation_node_schema import TreeNavigationNodeSchema

        d = src_dict.copy()

        def _parse_item(data: object) -> Union["TreeNavigationNodeSchema", None]:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                item_type_0 = TreeNavigationNodeSchema.from_dict(data)

                return item_type_0
            except:  # noqa: E722
                pass
            return cast(Union["TreeNavigationNodeSchema", None], data)

        item = _parse_item(d.pop("item"))

        children = []
        _children = d.pop("children")
        for children_item_data in _children:
            children_item = TreeNavigationNodeSchema.from_dict(children_item_data)

            children.append(children_item)

        children_count = d.pop("children_count")

        breadcrumbs = cast(List[str], d.pop("breadcrumbs"))

        is_leaf = d.pop("is_leaf")

        navigation_schema = cls(
            item=item,
            children=children,
            children_count=children_count,
            breadcrumbs=breadcrumbs,
            is_leaf=is_leaf,
        )

        navigation_schema.additional_properties = d
        return navigation_schema

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
