from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.resolve_parameters_response_schema_parameters import ResolveParametersResponseSchemaParameters


T = TypeVar("T", bound="ResolveParametersResponseSchema")


@_attrs_define
class ResolveParametersResponseSchema:
    """
    Attributes:
        path (str):
        version (int):
        requested_version (str):
        parameters (Union[Unset, ResolveParametersResponseSchemaParameters]):
    """

    path: str
    version: int
    requested_version: str
    parameters: Union[Unset, "ResolveParametersResponseSchemaParameters"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        path = self.path

        version = self.version

        requested_version = self.requested_version

        parameters: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.parameters, Unset):
            parameters = self.parameters.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "path": path,
                "version": version,
                "requested_version": requested_version,
            }
        )
        if parameters is not UNSET:
            field_dict["parameters"] = parameters

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.resolve_parameters_response_schema_parameters import ResolveParametersResponseSchemaParameters

        d = src_dict.copy()
        path = d.pop("path")

        version = d.pop("version")

        requested_version = d.pop("requested_version")

        _parameters = d.pop("parameters", UNSET)
        parameters: Union[Unset, ResolveParametersResponseSchemaParameters]
        if isinstance(_parameters, Unset):
            parameters = UNSET
        else:
            parameters = ResolveParametersResponseSchemaParameters.from_dict(_parameters)

        resolve_parameters_response_schema = cls(
            path=path,
            version=version,
            requested_version=requested_version,
            parameters=parameters,
        )

        resolve_parameters_response_schema.additional_properties = d
        return resolve_parameters_response_schema

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
