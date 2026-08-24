from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.global_permission_actor_schema import GlobalPermissionActorSchema


T = TypeVar("T", bound="GlobalPermissionSectionSchema")


@_attrs_define
class GlobalPermissionSectionSchema:
    """
    Attributes:
        actors (List['GlobalPermissionActorSchema']):
    """

    actors: List["GlobalPermissionActorSchema"]

    def to_dict(self) -> Dict[str, Any]:
        actors = []
        for actors_item_data in self.actors:
            actors_item = actors_item_data.to_dict()
            actors.append(actors_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(
            {
                "actors": actors,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.global_permission_actor_schema import GlobalPermissionActorSchema

        d = src_dict.copy()
        actors = []
        _actors = d.pop("actors")
        for actors_item_data in _actors:
            actors_item = GlobalPermissionActorSchema.from_dict(actors_item_data)

            actors.append(actors_item)

        global_permission_section_schema = cls(
            actors=actors,
        )

        return global_permission_section_schema
