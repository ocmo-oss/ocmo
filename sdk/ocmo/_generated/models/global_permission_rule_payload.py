from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.global_permission_section_schema import GlobalPermissionSectionSchema


T = TypeVar("T", bound="GlobalPermissionRulePayload")


@_attrs_define
class GlobalPermissionRulePayload:
    """
    Attributes:
        namespace (str): Namespace name glob pattern
        id (Union[None, Unset, str]):
        description (Union[None, Unset, str]):
        read (Union['GlobalPermissionSectionSchema', None, Unset]):
        write (Union['GlobalPermissionSectionSchema', None, Unset]):
        delete (Union['GlobalPermissionSectionSchema', None, Unset]):
        audit (Union['GlobalPermissionSectionSchema', None, Unset]):
    """

    namespace: str
    id: Union[None, Unset, str] = UNSET
    description: Union[None, Unset, str] = UNSET
    read: Union["GlobalPermissionSectionSchema", None, Unset] = UNSET
    write: Union["GlobalPermissionSectionSchema", None, Unset] = UNSET
    delete: Union["GlobalPermissionSectionSchema", None, Unset] = UNSET
    audit: Union["GlobalPermissionSectionSchema", None, Unset] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        from ..models.global_permission_section_schema import GlobalPermissionSectionSchema

        namespace = self.namespace

        id: Union[None, Unset, str]
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        description: Union[None, Unset, str]
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        read: Union[Dict[str, Any], None, Unset]
        if isinstance(self.read, Unset):
            read = UNSET
        elif isinstance(self.read, GlobalPermissionSectionSchema):
            read = self.read.to_dict()
        else:
            read = self.read

        write: Union[Dict[str, Any], None, Unset]
        if isinstance(self.write, Unset):
            write = UNSET
        elif isinstance(self.write, GlobalPermissionSectionSchema):
            write = self.write.to_dict()
        else:
            write = self.write

        delete: Union[Dict[str, Any], None, Unset]
        if isinstance(self.delete, Unset):
            delete = UNSET
        elif isinstance(self.delete, GlobalPermissionSectionSchema):
            delete = self.delete.to_dict()
        else:
            delete = self.delete

        audit: Union[Dict[str, Any], None, Unset]
        if isinstance(self.audit, Unset):
            audit = UNSET
        elif isinstance(self.audit, GlobalPermissionSectionSchema):
            audit = self.audit.to_dict()
        else:
            audit = self.audit

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "namespace": namespace,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if description is not UNSET:
            field_dict["description"] = description
        if read is not UNSET:
            field_dict["read"] = read
        if write is not UNSET:
            field_dict["write"] = write
        if delete is not UNSET:
            field_dict["delete"] = delete
        if audit is not UNSET:
            field_dict["audit"] = audit

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.global_permission_section_schema import GlobalPermissionSectionSchema

        d = src_dict.copy()
        namespace = d.pop("namespace")

        def _parse_id(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        id = _parse_id(d.pop("id", UNSET))

        def _parse_description(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        description = _parse_description(d.pop("description", UNSET))

        def _parse_read(data: object) -> Union["GlobalPermissionSectionSchema", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                read_type_0 = GlobalPermissionSectionSchema.from_dict(data)

                return read_type_0
            except:  # noqa: E722
                pass
            return cast(Union["GlobalPermissionSectionSchema", None, Unset], data)

        read = _parse_read(d.pop("read", UNSET))

        def _parse_write(data: object) -> Union["GlobalPermissionSectionSchema", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                write_type_0 = GlobalPermissionSectionSchema.from_dict(data)

                return write_type_0
            except:  # noqa: E722
                pass
            return cast(Union["GlobalPermissionSectionSchema", None, Unset], data)

        write = _parse_write(d.pop("write", UNSET))

        def _parse_delete(data: object) -> Union["GlobalPermissionSectionSchema", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                delete_type_0 = GlobalPermissionSectionSchema.from_dict(data)

                return delete_type_0
            except:  # noqa: E722
                pass
            return cast(Union["GlobalPermissionSectionSchema", None, Unset], data)

        delete = _parse_delete(d.pop("delete", UNSET))

        def _parse_audit(data: object) -> Union["GlobalPermissionSectionSchema", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                audit_type_0 = GlobalPermissionSectionSchema.from_dict(data)

                return audit_type_0
            except:  # noqa: E722
                pass
            return cast(Union["GlobalPermissionSectionSchema", None, Unset], data)

        audit = _parse_audit(d.pop("audit", UNSET))

        global_permission_rule_payload = cls(
            namespace=namespace,
            id=id,
            description=description,
            read=read,
            write=write,
            delete=delete,
            audit=audit,
        )

        global_permission_rule_payload.additional_properties = d
        return global_permission_rule_payload

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
