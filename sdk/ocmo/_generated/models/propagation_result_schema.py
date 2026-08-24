from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.propagation_target_result import PropagationTargetResult


T = TypeVar("T", bound="PropagationResultSchema")


@_attrs_define
class PropagationResultSchema:
    """
    Attributes:
        source_path (str):
        source_version (int):
        trigger (str):
        targets (List['PropagationTargetResult']):
    """

    source_path: str
    source_version: int
    trigger: str
    targets: List["PropagationTargetResult"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        source_path = self.source_path

        source_version = self.source_version

        trigger = self.trigger

        targets = []
        for targets_item_data in self.targets:
            targets_item = targets_item_data.to_dict()
            targets.append(targets_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "source_path": source_path,
                "source_version": source_version,
                "trigger": trigger,
                "targets": targets,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.propagation_target_result import PropagationTargetResult

        d = src_dict.copy()
        source_path = d.pop("source_path")

        source_version = d.pop("source_version")

        trigger = d.pop("trigger")

        targets = []
        _targets = d.pop("targets")
        for targets_item_data in _targets:
            targets_item = PropagationTargetResult.from_dict(targets_item_data)

            targets.append(targets_item)

        propagation_result_schema = cls(
            source_path=source_path,
            source_version=source_version,
            trigger=trigger,
            targets=targets,
        )

        propagation_result_schema.additional_properties = d
        return propagation_result_schema

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
