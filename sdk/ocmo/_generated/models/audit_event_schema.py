import datetime
from typing import Any, Dict, List, Type, TypeVar, Union, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="AuditEventSchema")


@_attrs_define
class AuditEventSchema:
    """
    Attributes:
        id (UUID):
        occurred_at (datetime.datetime):
        auth_id (str):
        auth_type (str):
        http_method (str):
        api_endpoint (str):
        event_kind (str):
        client_ip (Union[None, Unset, str]):
        user_agent (Union[None, Unset, str]):
        auth_email (Union[None, Unset, str]):
        token_number (Union[None, Unset, int]):
        namespace (Union[None, Unset, str]): Denormalized namespace name
        object_type (Union[None, Unset, str]):
        object_id (Union[None, Unset, str]):
        object_version (Union[None, Unset, int]):
        operation (Union[None, Unset, str]):
        subresource_type (Union[None, Unset, str]):
        subresource (Union[None, Unset, str]):
        permission_ok (Union[None, Unset, bool]):
        error (Union[None, Unset, str]):
        resolve_type (Union[None, Unset, str]):
        from_cache (Union[None, Unset, bool]):
        parent_event_id (Union[None, UUID, Unset]):
    """

    id: UUID
    occurred_at: datetime.datetime
    auth_id: str
    auth_type: str
    http_method: str
    api_endpoint: str
    event_kind: str
    client_ip: Union[None, Unset, str] = UNSET
    user_agent: Union[None, Unset, str] = UNSET
    auth_email: Union[None, Unset, str] = UNSET
    token_number: Union[None, Unset, int] = UNSET
    namespace: Union[None, Unset, str] = UNSET
    object_type: Union[None, Unset, str] = UNSET
    object_id: Union[None, Unset, str] = UNSET
    object_version: Union[None, Unset, int] = UNSET
    operation: Union[None, Unset, str] = UNSET
    subresource_type: Union[None, Unset, str] = UNSET
    subresource: Union[None, Unset, str] = UNSET
    permission_ok: Union[None, Unset, bool] = UNSET
    error: Union[None, Unset, str] = UNSET
    resolve_type: Union[None, Unset, str] = UNSET
    from_cache: Union[None, Unset, bool] = UNSET
    parent_event_id: Union[None, UUID, Unset] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = str(self.id)

        occurred_at = self.occurred_at.isoformat()

        auth_id = self.auth_id

        auth_type = self.auth_type

        http_method = self.http_method

        api_endpoint = self.api_endpoint

        event_kind = self.event_kind

        client_ip: Union[None, Unset, str]
        if isinstance(self.client_ip, Unset):
            client_ip = UNSET
        else:
            client_ip = self.client_ip

        user_agent: Union[None, Unset, str]
        if isinstance(self.user_agent, Unset):
            user_agent = UNSET
        else:
            user_agent = self.user_agent

        auth_email: Union[None, Unset, str]
        if isinstance(self.auth_email, Unset):
            auth_email = UNSET
        else:
            auth_email = self.auth_email

        token_number: Union[None, Unset, int]
        if isinstance(self.token_number, Unset):
            token_number = UNSET
        else:
            token_number = self.token_number

        namespace: Union[None, Unset, str]
        if isinstance(self.namespace, Unset):
            namespace = UNSET
        else:
            namespace = self.namespace

        object_type: Union[None, Unset, str]
        if isinstance(self.object_type, Unset):
            object_type = UNSET
        else:
            object_type = self.object_type

        object_id: Union[None, Unset, str]
        if isinstance(self.object_id, Unset):
            object_id = UNSET
        else:
            object_id = self.object_id

        object_version: Union[None, Unset, int]
        if isinstance(self.object_version, Unset):
            object_version = UNSET
        else:
            object_version = self.object_version

        operation: Union[None, Unset, str]
        if isinstance(self.operation, Unset):
            operation = UNSET
        else:
            operation = self.operation

        subresource_type: Union[None, Unset, str]
        if isinstance(self.subresource_type, Unset):
            subresource_type = UNSET
        else:
            subresource_type = self.subresource_type

        subresource: Union[None, Unset, str]
        if isinstance(self.subresource, Unset):
            subresource = UNSET
        else:
            subresource = self.subresource

        permission_ok: Union[None, Unset, bool]
        if isinstance(self.permission_ok, Unset):
            permission_ok = UNSET
        else:
            permission_ok = self.permission_ok

        error: Union[None, Unset, str]
        if isinstance(self.error, Unset):
            error = UNSET
        else:
            error = self.error

        resolve_type: Union[None, Unset, str]
        if isinstance(self.resolve_type, Unset):
            resolve_type = UNSET
        else:
            resolve_type = self.resolve_type

        from_cache: Union[None, Unset, bool]
        if isinstance(self.from_cache, Unset):
            from_cache = UNSET
        else:
            from_cache = self.from_cache

        parent_event_id: Union[None, Unset, str]
        if isinstance(self.parent_event_id, Unset):
            parent_event_id = UNSET
        elif isinstance(self.parent_event_id, UUID):
            parent_event_id = str(self.parent_event_id)
        else:
            parent_event_id = self.parent_event_id

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "occurred_at": occurred_at,
                "auth_id": auth_id,
                "auth_type": auth_type,
                "http_method": http_method,
                "api_endpoint": api_endpoint,
                "event_kind": event_kind,
            }
        )
        if client_ip is not UNSET:
            field_dict["client_ip"] = client_ip
        if user_agent is not UNSET:
            field_dict["user_agent"] = user_agent
        if auth_email is not UNSET:
            field_dict["auth_email"] = auth_email
        if token_number is not UNSET:
            field_dict["token_number"] = token_number
        if namespace is not UNSET:
            field_dict["namespace"] = namespace
        if object_type is not UNSET:
            field_dict["object_type"] = object_type
        if object_id is not UNSET:
            field_dict["object_id"] = object_id
        if object_version is not UNSET:
            field_dict["object_version"] = object_version
        if operation is not UNSET:
            field_dict["operation"] = operation
        if subresource_type is not UNSET:
            field_dict["subresource_type"] = subresource_type
        if subresource is not UNSET:
            field_dict["subresource"] = subresource
        if permission_ok is not UNSET:
            field_dict["permission_ok"] = permission_ok
        if error is not UNSET:
            field_dict["error"] = error
        if resolve_type is not UNSET:
            field_dict["resolve_type"] = resolve_type
        if from_cache is not UNSET:
            field_dict["from_cache"] = from_cache
        if parent_event_id is not UNSET:
            field_dict["parent_event_id"] = parent_event_id

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        id = UUID(d.pop("id"))

        occurred_at = isoparse(d.pop("occurred_at"))

        auth_id = d.pop("auth_id")

        auth_type = d.pop("auth_type")

        http_method = d.pop("http_method")

        api_endpoint = d.pop("api_endpoint")

        event_kind = d.pop("event_kind")

        def _parse_client_ip(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        client_ip = _parse_client_ip(d.pop("client_ip", UNSET))

        def _parse_user_agent(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        user_agent = _parse_user_agent(d.pop("user_agent", UNSET))

        def _parse_auth_email(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        auth_email = _parse_auth_email(d.pop("auth_email", UNSET))

        def _parse_token_number(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        token_number = _parse_token_number(d.pop("token_number", UNSET))

        def _parse_namespace(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        namespace = _parse_namespace(d.pop("namespace", UNSET))

        def _parse_object_type(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        object_type = _parse_object_type(d.pop("object_type", UNSET))

        def _parse_object_id(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        object_id = _parse_object_id(d.pop("object_id", UNSET))

        def _parse_object_version(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        object_version = _parse_object_version(d.pop("object_version", UNSET))

        def _parse_operation(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        operation = _parse_operation(d.pop("operation", UNSET))

        def _parse_subresource_type(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        subresource_type = _parse_subresource_type(d.pop("subresource_type", UNSET))

        def _parse_subresource(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        subresource = _parse_subresource(d.pop("subresource", UNSET))

        def _parse_permission_ok(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        permission_ok = _parse_permission_ok(d.pop("permission_ok", UNSET))

        def _parse_error(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        error = _parse_error(d.pop("error", UNSET))

        def _parse_resolve_type(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        resolve_type = _parse_resolve_type(d.pop("resolve_type", UNSET))

        def _parse_from_cache(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        from_cache = _parse_from_cache(d.pop("from_cache", UNSET))

        def _parse_parent_event_id(data: object) -> Union[None, UUID, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                parent_event_id_type_0 = UUID(data)

                return parent_event_id_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, UUID, Unset], data)

        parent_event_id = _parse_parent_event_id(d.pop("parent_event_id", UNSET))

        audit_event_schema = cls(
            id=id,
            occurred_at=occurred_at,
            auth_id=auth_id,
            auth_type=auth_type,
            http_method=http_method,
            api_endpoint=api_endpoint,
            event_kind=event_kind,
            client_ip=client_ip,
            user_agent=user_agent,
            auth_email=auth_email,
            token_number=token_number,
            namespace=namespace,
            object_type=object_type,
            object_id=object_id,
            object_version=object_version,
            operation=operation,
            subresource_type=subresource_type,
            subresource=subresource,
            permission_ok=permission_ok,
            error=error,
            resolve_type=resolve_type,
            from_cache=from_cache,
            parent_event_id=parent_event_id,
        )

        audit_event_schema.additional_properties = d
        return audit_event_schema

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
