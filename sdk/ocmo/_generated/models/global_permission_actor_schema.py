from typing import TYPE_CHECKING, Any, Dict, Literal, Type, TypeVar, cast

from attrs import define as _attrs_define

if TYPE_CHECKING:
    from ..models.global_permission_actor_schema_claims import GlobalPermissionActorSchemaClaims


T = TypeVar("T", bound="GlobalPermissionActorSchema")


@_attrs_define
class GlobalPermissionActorSchema:
    """
    Attributes:
        kind (Literal['User']):
        claims (GlobalPermissionActorSchemaClaims):
    """

    kind: Literal["User"]
    claims: "GlobalPermissionActorSchemaClaims"

    def to_dict(self) -> Dict[str, Any]:
        kind = self.kind

        claims = self.claims.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(
            {
                "kind": kind,
                "claims": claims,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.global_permission_actor_schema_claims import GlobalPermissionActorSchemaClaims

        d = src_dict.copy()
        kind = cast(Literal["User"], d.pop("kind"))
        if kind != "User":
            raise ValueError(f"kind must match const 'User', got '{kind}'")

        claims = GlobalPermissionActorSchemaClaims.from_dict(d.pop("claims"))

        global_permission_actor_schema = cls(
            kind=kind,
            claims=claims,
        )

        return global_permission_actor_schema
