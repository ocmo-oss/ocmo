from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.effective_resolver_schema import EffectiveResolverSchema
    from ..models.resolve_response_schema_root_type_0 import ResolveResponseSchemaRootType0
    from ..models.resolved_item_schema import ResolvedItemSchema


T = TypeVar("T", bound="ResolveResponseSchema")


@_attrs_define
class ResolveResponseSchema:
    """
    Attributes:
        items (List['ResolvedItemSchema']):
        length (int):
        trace_only (Union[None, Unset, bool]):
        root (Union['ResolveResponseSchemaRootType0', None, Unset]):
        resolver (Union['EffectiveResolverSchema', None, Unset]):
    """

    items: List["ResolvedItemSchema"]
    length: int
    trace_only: Union[None, Unset, bool] = UNSET
    root: Union["ResolveResponseSchemaRootType0", None, Unset] = UNSET
    resolver: Union["EffectiveResolverSchema", None, Unset] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        from ..models.effective_resolver_schema import EffectiveResolverSchema
        from ..models.resolve_response_schema_root_type_0 import ResolveResponseSchemaRootType0

        items = []
        for items_item_data in self.items:
            items_item = items_item_data.to_dict()
            items.append(items_item)

        length = self.length

        trace_only: Union[None, Unset, bool]
        if isinstance(self.trace_only, Unset):
            trace_only = UNSET
        else:
            trace_only = self.trace_only

        root: Union[Dict[str, Any], None, Unset]
        if isinstance(self.root, Unset):
            root = UNSET
        elif isinstance(self.root, ResolveResponseSchemaRootType0):
            root = self.root.to_dict()
        else:
            root = self.root

        resolver: Union[Dict[str, Any], None, Unset]
        if isinstance(self.resolver, Unset):
            resolver = UNSET
        elif isinstance(self.resolver, EffectiveResolverSchema):
            resolver = self.resolver.to_dict()
        else:
            resolver = self.resolver

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "items": items,
                "length": length,
            }
        )
        if trace_only is not UNSET:
            field_dict["trace_only"] = trace_only
        if root is not UNSET:
            field_dict["root"] = root
        if resolver is not UNSET:
            field_dict["resolver"] = resolver

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.effective_resolver_schema import EffectiveResolverSchema
        from ..models.resolve_response_schema_root_type_0 import ResolveResponseSchemaRootType0
        from ..models.resolved_item_schema import ResolvedItemSchema

        d = src_dict.copy()
        items = []
        _items = d.pop("items")
        for items_item_data in _items:
            items_item = ResolvedItemSchema.from_dict(items_item_data)

            items.append(items_item)

        length = d.pop("length")

        def _parse_trace_only(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        trace_only = _parse_trace_only(d.pop("trace_only", UNSET))

        def _parse_root(data: object) -> Union["ResolveResponseSchemaRootType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                root_type_0 = ResolveResponseSchemaRootType0.from_dict(data)

                return root_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ResolveResponseSchemaRootType0", None, Unset], data)

        root = _parse_root(d.pop("root", UNSET))

        def _parse_resolver(data: object) -> Union["EffectiveResolverSchema", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                resolver_type_0 = EffectiveResolverSchema.from_dict(data)

                return resolver_type_0
            except:  # noqa: E722
                pass
            return cast(Union["EffectiveResolverSchema", None, Unset], data)

        resolver = _parse_resolver(d.pop("resolver", UNSET))

        resolve_response_schema = cls(
            items=items,
            length=length,
            trace_only=trace_only,
            root=root,
            resolver=resolver,
        )

        resolve_response_schema.additional_properties = d
        return resolve_response_schema

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
