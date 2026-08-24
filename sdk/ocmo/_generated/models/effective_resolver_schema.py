from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.effective_resolver_hooks_schema import EffectiveResolverHooksSchema
    from ..models.effective_resolver_schema_parameters_type_0 import EffectiveResolverSchemaParametersType0


T = TypeVar("T", bound="EffectiveResolverSchema")


@_attrs_define
class EffectiveResolverSchema:
    """Effective resolver configuration for a resolver-authenticated resolve call.

    Attributes:
        cast (Union[None, Unset, str]):
        parameters (Union['EffectiveResolverSchemaParametersType0', None, Unset]):
        hooks (Union['EffectiveResolverHooksSchema', None, Unset]):
    """

    cast: Union[None, Unset, str] = UNSET
    parameters: Union["EffectiveResolverSchemaParametersType0", None, Unset] = UNSET
    hooks: Union["EffectiveResolverHooksSchema", None, Unset] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        from ..models.effective_resolver_hooks_schema import EffectiveResolverHooksSchema
        from ..models.effective_resolver_schema_parameters_type_0 import EffectiveResolverSchemaParametersType0

        cast: Union[None, Unset, str]
        if isinstance(self.cast, Unset):
            cast = UNSET
        else:
            cast = self.cast

        parameters: Union[Dict[str, Any], None, Unset]
        if isinstance(self.parameters, Unset):
            parameters = UNSET
        elif isinstance(self.parameters, EffectiveResolverSchemaParametersType0):
            parameters = self.parameters.to_dict()
        else:
            parameters = self.parameters

        hooks: Union[Dict[str, Any], None, Unset]
        if isinstance(self.hooks, Unset):
            hooks = UNSET
        elif isinstance(self.hooks, EffectiveResolverHooksSchema):
            hooks = self.hooks.to_dict()
        else:
            hooks = self.hooks

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if cast is not UNSET:
            field_dict["cast"] = cast
        if parameters is not UNSET:
            field_dict["parameters"] = parameters
        if hooks is not UNSET:
            field_dict["hooks"] = hooks

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.effective_resolver_hooks_schema import EffectiveResolverHooksSchema
        from ..models.effective_resolver_schema_parameters_type_0 import EffectiveResolverSchemaParametersType0

        d = src_dict.copy()

        def _parse_cast(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        cast = _parse_cast(d.pop("cast", UNSET))

        def _parse_parameters(data: object) -> Union["EffectiveResolverSchemaParametersType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                parameters_type_0 = EffectiveResolverSchemaParametersType0.from_dict(data)

                return parameters_type_0
            except:  # noqa: E722
                pass
            return cast(Union["EffectiveResolverSchemaParametersType0", None, Unset], data)

        parameters = _parse_parameters(d.pop("parameters", UNSET))

        def _parse_hooks(data: object) -> Union["EffectiveResolverHooksSchema", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                hooks_type_0 = EffectiveResolverHooksSchema.from_dict(data)

                return hooks_type_0
            except:  # noqa: E722
                pass
            return cast(Union["EffectiveResolverHooksSchema", None, Unset], data)

        hooks = _parse_hooks(d.pop("hooks", UNSET))

        effective_resolver_schema = cls(
            cast=cast,
            parameters=parameters,
            hooks=hooks,
        )

        effective_resolver_schema.additional_properties = d
        return effective_resolver_schema

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
