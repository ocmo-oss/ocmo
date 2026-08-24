from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.health_schema_status import HealthSchemaStatus

if TYPE_CHECKING:
    from ..models.health_schema_checks import HealthSchemaChecks


T = TypeVar("T", bound="HealthSchema")


@_attrs_define
class HealthSchema:
    """
    Attributes:
        status (HealthSchemaStatus): Overall health: ok when all checks pass
        checks (HealthSchemaChecks): Per-component health results
    """

    status: HealthSchemaStatus
    checks: "HealthSchemaChecks"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        status = self.status.value

        checks = self.checks.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "status": status,
                "checks": checks,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.health_schema_checks import HealthSchemaChecks

        d = src_dict.copy()
        status = HealthSchemaStatus(d.pop("status"))

        checks = HealthSchemaChecks.from_dict(d.pop("checks"))

        health_schema = cls(
            status=status,
            checks=checks,
        )

        health_schema.additional_properties = d
        return health_schema

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
