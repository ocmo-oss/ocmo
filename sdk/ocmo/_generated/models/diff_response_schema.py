from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.diff_side_schema import DiffSideSchema


T = TypeVar("T", bound="DiffResponseSchema")


@_attrs_define
class DiffResponseSchema:
    """Compare two versions or two paths; client renders the diff from both sides.

    Attributes:
        path (str): Primary path from the URL
        from_side (DiffSideSchema): One side of a tree item diff (path, resolved version, optional content).
        to_side (DiffSideSchema): One side of a tree item diff (path, resolved version, optional content).
        to_path (Union[None, Unset, str]): Second path when ?to_path= is used for cross-item diff
        identical (Union[None, Unset, bool]): True when both sides have comparable plaintext and content matches
        decryption_required (Union[Unset, bool]): True for secret diff without ?reveal=true; content is not returned
            Default: False.
    """

    path: str
    from_side: "DiffSideSchema"
    to_side: "DiffSideSchema"
    to_path: Union[None, Unset, str] = UNSET
    identical: Union[None, Unset, bool] = UNSET
    decryption_required: Union[Unset, bool] = False
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        path = self.path

        from_side = self.from_side.to_dict()

        to_side = self.to_side.to_dict()

        to_path: Union[None, Unset, str]
        if isinstance(self.to_path, Unset):
            to_path = UNSET
        else:
            to_path = self.to_path

        identical: Union[None, Unset, bool]
        if isinstance(self.identical, Unset):
            identical = UNSET
        else:
            identical = self.identical

        decryption_required = self.decryption_required

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "path": path,
                "from_side": from_side,
                "to_side": to_side,
            }
        )
        if to_path is not UNSET:
            field_dict["to_path"] = to_path
        if identical is not UNSET:
            field_dict["identical"] = identical
        if decryption_required is not UNSET:
            field_dict["decryption_required"] = decryption_required

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.diff_side_schema import DiffSideSchema

        d = src_dict.copy()
        path = d.pop("path")

        from_side = DiffSideSchema.from_dict(d.pop("from_side"))

        to_side = DiffSideSchema.from_dict(d.pop("to_side"))

        def _parse_to_path(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        to_path = _parse_to_path(d.pop("to_path", UNSET))

        def _parse_identical(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        identical = _parse_identical(d.pop("identical", UNSET))

        decryption_required = d.pop("decryption_required", UNSET)

        diff_response_schema = cls(
            path=path,
            from_side=from_side,
            to_side=to_side,
            to_path=to_path,
            identical=identical,
            decryption_required=decryption_required,
        )

        diff_response_schema.additional_properties = d
        return diff_response_schema

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
