import datetime
from http import HTTPStatus
from typing import Any, Dict, Optional, Union
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.paged_audit_event_schema import PagedAuditEventSchema
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    auth_id: Union[None, Unset, str] = UNSET,
    auth_email: Union[None, Unset, str] = UNSET,
    auth_type: Union[None, Unset, str] = UNSET,
    object_type: Union[None, Unset, str] = UNSET,
    object_id: Union[None, Unset, str] = UNSET,
    http_method: Union[None, Unset, str] = UNSET,
    api_endpoint: Union[None, Unset, str] = UNSET,
    permission_ok: Union[None, Unset, bool] = UNSET,
    resolve_type: Union[None, Unset, str] = UNSET,
    from_cache: Union[None, Unset, bool] = UNSET,
    event_kind: Union[None, Unset, str] = UNSET,
    category: Union[None, Unset, str] = UNSET,
    parent_event_id: Union[None, UUID, Unset] = UNSET,
    client_ip: Union[None, Unset, str] = UNSET,
    user_agent: Union[None, Unset, str] = UNSET,
    token_number: Union[None, Unset, int] = UNSET,
    object_version: Union[None, Unset, int] = UNSET,
    operation: Union[None, Unset, str] = UNSET,
    subresource_type: Union[None, Unset, str] = UNSET,
    subresource: Union[None, Unset, str] = UNSET,
    event_id: Union[None, UUID, Unset] = UNSET,
    error: Union[None, Unset, str] = UNSET,
    namespace: Union[None, Unset, str] = UNSET,
    search: Union[None, Unset, str] = UNSET,
    from_: Union[None, Unset, datetime.datetime] = UNSET,
    to: Union[None, Unset, datetime.datetime] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    json_auth_id: Union[None, Unset, str]
    if isinstance(auth_id, Unset):
        json_auth_id = UNSET
    else:
        json_auth_id = auth_id
    params["auth_id"] = json_auth_id

    json_auth_email: Union[None, Unset, str]
    if isinstance(auth_email, Unset):
        json_auth_email = UNSET
    else:
        json_auth_email = auth_email
    params["auth_email"] = json_auth_email

    json_auth_type: Union[None, Unset, str]
    if isinstance(auth_type, Unset):
        json_auth_type = UNSET
    else:
        json_auth_type = auth_type
    params["auth_type"] = json_auth_type

    json_object_type: Union[None, Unset, str]
    if isinstance(object_type, Unset):
        json_object_type = UNSET
    else:
        json_object_type = object_type
    params["object_type"] = json_object_type

    json_object_id: Union[None, Unset, str]
    if isinstance(object_id, Unset):
        json_object_id = UNSET
    else:
        json_object_id = object_id
    params["object_id"] = json_object_id

    json_http_method: Union[None, Unset, str]
    if isinstance(http_method, Unset):
        json_http_method = UNSET
    else:
        json_http_method = http_method
    params["http_method"] = json_http_method

    json_api_endpoint: Union[None, Unset, str]
    if isinstance(api_endpoint, Unset):
        json_api_endpoint = UNSET
    else:
        json_api_endpoint = api_endpoint
    params["api_endpoint"] = json_api_endpoint

    json_permission_ok: Union[None, Unset, bool]
    if isinstance(permission_ok, Unset):
        json_permission_ok = UNSET
    else:
        json_permission_ok = permission_ok
    params["permission_ok"] = json_permission_ok

    json_resolve_type: Union[None, Unset, str]
    if isinstance(resolve_type, Unset):
        json_resolve_type = UNSET
    else:
        json_resolve_type = resolve_type
    params["resolve_type"] = json_resolve_type

    json_from_cache: Union[None, Unset, bool]
    if isinstance(from_cache, Unset):
        json_from_cache = UNSET
    else:
        json_from_cache = from_cache
    params["from_cache"] = json_from_cache

    json_event_kind: Union[None, Unset, str]
    if isinstance(event_kind, Unset):
        json_event_kind = UNSET
    else:
        json_event_kind = event_kind
    params["event_kind"] = json_event_kind

    json_category: Union[None, Unset, str]
    if isinstance(category, Unset):
        json_category = UNSET
    else:
        json_category = category
    params["category"] = json_category

    json_parent_event_id: Union[None, Unset, str]
    if isinstance(parent_event_id, Unset):
        json_parent_event_id = UNSET
    elif isinstance(parent_event_id, UUID):
        json_parent_event_id = str(parent_event_id)
    else:
        json_parent_event_id = parent_event_id
    params["parent_event_id"] = json_parent_event_id

    json_client_ip: Union[None, Unset, str]
    if isinstance(client_ip, Unset):
        json_client_ip = UNSET
    else:
        json_client_ip = client_ip
    params["client_ip"] = json_client_ip

    json_user_agent: Union[None, Unset, str]
    if isinstance(user_agent, Unset):
        json_user_agent = UNSET
    else:
        json_user_agent = user_agent
    params["user_agent"] = json_user_agent

    json_token_number: Union[None, Unset, int]
    if isinstance(token_number, Unset):
        json_token_number = UNSET
    else:
        json_token_number = token_number
    params["token_number"] = json_token_number

    json_object_version: Union[None, Unset, int]
    if isinstance(object_version, Unset):
        json_object_version = UNSET
    else:
        json_object_version = object_version
    params["object_version"] = json_object_version

    json_operation: Union[None, Unset, str]
    if isinstance(operation, Unset):
        json_operation = UNSET
    else:
        json_operation = operation
    params["operation"] = json_operation

    json_subresource_type: Union[None, Unset, str]
    if isinstance(subresource_type, Unset):
        json_subresource_type = UNSET
    else:
        json_subresource_type = subresource_type
    params["subresource_type"] = json_subresource_type

    json_subresource: Union[None, Unset, str]
    if isinstance(subresource, Unset):
        json_subresource = UNSET
    else:
        json_subresource = subresource
    params["subresource"] = json_subresource

    json_event_id: Union[None, Unset, str]
    if isinstance(event_id, Unset):
        json_event_id = UNSET
    elif isinstance(event_id, UUID):
        json_event_id = str(event_id)
    else:
        json_event_id = event_id
    params["event_id"] = json_event_id

    json_error: Union[None, Unset, str]
    if isinstance(error, Unset):
        json_error = UNSET
    else:
        json_error = error
    params["error"] = json_error

    json_namespace: Union[None, Unset, str]
    if isinstance(namespace, Unset):
        json_namespace = UNSET
    else:
        json_namespace = namespace
    params["namespace"] = json_namespace

    json_search: Union[None, Unset, str]
    if isinstance(search, Unset):
        json_search = UNSET
    else:
        json_search = search
    params["search"] = json_search

    json_from_: Union[None, Unset, str]
    if isinstance(from_, Unset):
        json_from_ = UNSET
    elif isinstance(from_, datetime.datetime):
        json_from_ = from_.isoformat()
    else:
        json_from_ = from_
    params["from"] = json_from_

    json_to: Union[None, Unset, str]
    if isinstance(to, Unset):
        json_to = UNSET
    elif isinstance(to, datetime.datetime):
        json_to = to.isoformat()
    else:
        json_to = to
    params["to"] = json_to

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/audit/",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[PagedAuditEventSchema]:
    if response.status_code == 200:
        response_200 = PagedAuditEventSchema.from_dict(response.json())

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[PagedAuditEventSchema]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    auth_id: Union[None, Unset, str] = UNSET,
    auth_email: Union[None, Unset, str] = UNSET,
    auth_type: Union[None, Unset, str] = UNSET,
    object_type: Union[None, Unset, str] = UNSET,
    object_id: Union[None, Unset, str] = UNSET,
    http_method: Union[None, Unset, str] = UNSET,
    api_endpoint: Union[None, Unset, str] = UNSET,
    permission_ok: Union[None, Unset, bool] = UNSET,
    resolve_type: Union[None, Unset, str] = UNSET,
    from_cache: Union[None, Unset, bool] = UNSET,
    event_kind: Union[None, Unset, str] = UNSET,
    category: Union[None, Unset, str] = UNSET,
    parent_event_id: Union[None, UUID, Unset] = UNSET,
    client_ip: Union[None, Unset, str] = UNSET,
    user_agent: Union[None, Unset, str] = UNSET,
    token_number: Union[None, Unset, int] = UNSET,
    object_version: Union[None, Unset, int] = UNSET,
    operation: Union[None, Unset, str] = UNSET,
    subresource_type: Union[None, Unset, str] = UNSET,
    subresource: Union[None, Unset, str] = UNSET,
    event_id: Union[None, UUID, Unset] = UNSET,
    error: Union[None, Unset, str] = UNSET,
    namespace: Union[None, Unset, str] = UNSET,
    search: Union[None, Unset, str] = UNSET,
    from_: Union[None, Unset, datetime.datetime] = UNSET,
    to: Union[None, Unset, datetime.datetime] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Response[PagedAuditEventSchema]:
    """List Global Audit

     Cross-namespace audit log (global admin only).

    Args:
        auth_id (Union[None, Unset, str]):
        auth_email (Union[None, Unset, str]):
        auth_type (Union[None, Unset, str]):
        object_type (Union[None, Unset, str]):
        object_id (Union[None, Unset, str]):
        http_method (Union[None, Unset, str]):
        api_endpoint (Union[None, Unset, str]):
        permission_ok (Union[None, Unset, bool]):
        resolve_type (Union[None, Unset, str]):
        from_cache (Union[None, Unset, bool]):
        event_kind (Union[None, Unset, str]):
        category (Union[None, Unset, str]):
        parent_event_id (Union[None, UUID, Unset]):
        client_ip (Union[None, Unset, str]):
        user_agent (Union[None, Unset, str]):
        token_number (Union[None, Unset, int]):
        object_version (Union[None, Unset, int]):
        operation (Union[None, Unset, str]):
        subresource_type (Union[None, Unset, str]):
        subresource (Union[None, Unset, str]):
        event_id (Union[None, UUID, Unset]):
        error (Union[None, Unset, str]):
        namespace (Union[None, Unset, str]):
        search (Union[None, Unset, str]):
        from_ (Union[None, Unset, datetime.datetime]):
        to (Union[None, Unset, datetime.datetime]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PagedAuditEventSchema]
    """

    kwargs = _get_kwargs(
        auth_id=auth_id,
        auth_email=auth_email,
        auth_type=auth_type,
        object_type=object_type,
        object_id=object_id,
        http_method=http_method,
        api_endpoint=api_endpoint,
        permission_ok=permission_ok,
        resolve_type=resolve_type,
        from_cache=from_cache,
        event_kind=event_kind,
        category=category,
        parent_event_id=parent_event_id,
        client_ip=client_ip,
        user_agent=user_agent,
        token_number=token_number,
        object_version=object_version,
        operation=operation,
        subresource_type=subresource_type,
        subresource=subresource,
        event_id=event_id,
        error=error,
        namespace=namespace,
        search=search,
        from_=from_,
        to=to,
        limit=limit,
        offset=offset,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    auth_id: Union[None, Unset, str] = UNSET,
    auth_email: Union[None, Unset, str] = UNSET,
    auth_type: Union[None, Unset, str] = UNSET,
    object_type: Union[None, Unset, str] = UNSET,
    object_id: Union[None, Unset, str] = UNSET,
    http_method: Union[None, Unset, str] = UNSET,
    api_endpoint: Union[None, Unset, str] = UNSET,
    permission_ok: Union[None, Unset, bool] = UNSET,
    resolve_type: Union[None, Unset, str] = UNSET,
    from_cache: Union[None, Unset, bool] = UNSET,
    event_kind: Union[None, Unset, str] = UNSET,
    category: Union[None, Unset, str] = UNSET,
    parent_event_id: Union[None, UUID, Unset] = UNSET,
    client_ip: Union[None, Unset, str] = UNSET,
    user_agent: Union[None, Unset, str] = UNSET,
    token_number: Union[None, Unset, int] = UNSET,
    object_version: Union[None, Unset, int] = UNSET,
    operation: Union[None, Unset, str] = UNSET,
    subresource_type: Union[None, Unset, str] = UNSET,
    subresource: Union[None, Unset, str] = UNSET,
    event_id: Union[None, UUID, Unset] = UNSET,
    error: Union[None, Unset, str] = UNSET,
    namespace: Union[None, Unset, str] = UNSET,
    search: Union[None, Unset, str] = UNSET,
    from_: Union[None, Unset, datetime.datetime] = UNSET,
    to: Union[None, Unset, datetime.datetime] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Optional[PagedAuditEventSchema]:
    """List Global Audit

     Cross-namespace audit log (global admin only).

    Args:
        auth_id (Union[None, Unset, str]):
        auth_email (Union[None, Unset, str]):
        auth_type (Union[None, Unset, str]):
        object_type (Union[None, Unset, str]):
        object_id (Union[None, Unset, str]):
        http_method (Union[None, Unset, str]):
        api_endpoint (Union[None, Unset, str]):
        permission_ok (Union[None, Unset, bool]):
        resolve_type (Union[None, Unset, str]):
        from_cache (Union[None, Unset, bool]):
        event_kind (Union[None, Unset, str]):
        category (Union[None, Unset, str]):
        parent_event_id (Union[None, UUID, Unset]):
        client_ip (Union[None, Unset, str]):
        user_agent (Union[None, Unset, str]):
        token_number (Union[None, Unset, int]):
        object_version (Union[None, Unset, int]):
        operation (Union[None, Unset, str]):
        subresource_type (Union[None, Unset, str]):
        subresource (Union[None, Unset, str]):
        event_id (Union[None, UUID, Unset]):
        error (Union[None, Unset, str]):
        namespace (Union[None, Unset, str]):
        search (Union[None, Unset, str]):
        from_ (Union[None, Unset, datetime.datetime]):
        to (Union[None, Unset, datetime.datetime]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PagedAuditEventSchema
    """

    return sync_detailed(
        client=client,
        auth_id=auth_id,
        auth_email=auth_email,
        auth_type=auth_type,
        object_type=object_type,
        object_id=object_id,
        http_method=http_method,
        api_endpoint=api_endpoint,
        permission_ok=permission_ok,
        resolve_type=resolve_type,
        from_cache=from_cache,
        event_kind=event_kind,
        category=category,
        parent_event_id=parent_event_id,
        client_ip=client_ip,
        user_agent=user_agent,
        token_number=token_number,
        object_version=object_version,
        operation=operation,
        subresource_type=subresource_type,
        subresource=subresource,
        event_id=event_id,
        error=error,
        namespace=namespace,
        search=search,
        from_=from_,
        to=to,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    auth_id: Union[None, Unset, str] = UNSET,
    auth_email: Union[None, Unset, str] = UNSET,
    auth_type: Union[None, Unset, str] = UNSET,
    object_type: Union[None, Unset, str] = UNSET,
    object_id: Union[None, Unset, str] = UNSET,
    http_method: Union[None, Unset, str] = UNSET,
    api_endpoint: Union[None, Unset, str] = UNSET,
    permission_ok: Union[None, Unset, bool] = UNSET,
    resolve_type: Union[None, Unset, str] = UNSET,
    from_cache: Union[None, Unset, bool] = UNSET,
    event_kind: Union[None, Unset, str] = UNSET,
    category: Union[None, Unset, str] = UNSET,
    parent_event_id: Union[None, UUID, Unset] = UNSET,
    client_ip: Union[None, Unset, str] = UNSET,
    user_agent: Union[None, Unset, str] = UNSET,
    token_number: Union[None, Unset, int] = UNSET,
    object_version: Union[None, Unset, int] = UNSET,
    operation: Union[None, Unset, str] = UNSET,
    subresource_type: Union[None, Unset, str] = UNSET,
    subresource: Union[None, Unset, str] = UNSET,
    event_id: Union[None, UUID, Unset] = UNSET,
    error: Union[None, Unset, str] = UNSET,
    namespace: Union[None, Unset, str] = UNSET,
    search: Union[None, Unset, str] = UNSET,
    from_: Union[None, Unset, datetime.datetime] = UNSET,
    to: Union[None, Unset, datetime.datetime] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Response[PagedAuditEventSchema]:
    """List Global Audit

     Cross-namespace audit log (global admin only).

    Args:
        auth_id (Union[None, Unset, str]):
        auth_email (Union[None, Unset, str]):
        auth_type (Union[None, Unset, str]):
        object_type (Union[None, Unset, str]):
        object_id (Union[None, Unset, str]):
        http_method (Union[None, Unset, str]):
        api_endpoint (Union[None, Unset, str]):
        permission_ok (Union[None, Unset, bool]):
        resolve_type (Union[None, Unset, str]):
        from_cache (Union[None, Unset, bool]):
        event_kind (Union[None, Unset, str]):
        category (Union[None, Unset, str]):
        parent_event_id (Union[None, UUID, Unset]):
        client_ip (Union[None, Unset, str]):
        user_agent (Union[None, Unset, str]):
        token_number (Union[None, Unset, int]):
        object_version (Union[None, Unset, int]):
        operation (Union[None, Unset, str]):
        subresource_type (Union[None, Unset, str]):
        subresource (Union[None, Unset, str]):
        event_id (Union[None, UUID, Unset]):
        error (Union[None, Unset, str]):
        namespace (Union[None, Unset, str]):
        search (Union[None, Unset, str]):
        from_ (Union[None, Unset, datetime.datetime]):
        to (Union[None, Unset, datetime.datetime]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[PagedAuditEventSchema]
    """

    kwargs = _get_kwargs(
        auth_id=auth_id,
        auth_email=auth_email,
        auth_type=auth_type,
        object_type=object_type,
        object_id=object_id,
        http_method=http_method,
        api_endpoint=api_endpoint,
        permission_ok=permission_ok,
        resolve_type=resolve_type,
        from_cache=from_cache,
        event_kind=event_kind,
        category=category,
        parent_event_id=parent_event_id,
        client_ip=client_ip,
        user_agent=user_agent,
        token_number=token_number,
        object_version=object_version,
        operation=operation,
        subresource_type=subresource_type,
        subresource=subresource,
        event_id=event_id,
        error=error,
        namespace=namespace,
        search=search,
        from_=from_,
        to=to,
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    auth_id: Union[None, Unset, str] = UNSET,
    auth_email: Union[None, Unset, str] = UNSET,
    auth_type: Union[None, Unset, str] = UNSET,
    object_type: Union[None, Unset, str] = UNSET,
    object_id: Union[None, Unset, str] = UNSET,
    http_method: Union[None, Unset, str] = UNSET,
    api_endpoint: Union[None, Unset, str] = UNSET,
    permission_ok: Union[None, Unset, bool] = UNSET,
    resolve_type: Union[None, Unset, str] = UNSET,
    from_cache: Union[None, Unset, bool] = UNSET,
    event_kind: Union[None, Unset, str] = UNSET,
    category: Union[None, Unset, str] = UNSET,
    parent_event_id: Union[None, UUID, Unset] = UNSET,
    client_ip: Union[None, Unset, str] = UNSET,
    user_agent: Union[None, Unset, str] = UNSET,
    token_number: Union[None, Unset, int] = UNSET,
    object_version: Union[None, Unset, int] = UNSET,
    operation: Union[None, Unset, str] = UNSET,
    subresource_type: Union[None, Unset, str] = UNSET,
    subresource: Union[None, Unset, str] = UNSET,
    event_id: Union[None, UUID, Unset] = UNSET,
    error: Union[None, Unset, str] = UNSET,
    namespace: Union[None, Unset, str] = UNSET,
    search: Union[None, Unset, str] = UNSET,
    from_: Union[None, Unset, datetime.datetime] = UNSET,
    to: Union[None, Unset, datetime.datetime] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Optional[PagedAuditEventSchema]:
    """List Global Audit

     Cross-namespace audit log (global admin only).

    Args:
        auth_id (Union[None, Unset, str]):
        auth_email (Union[None, Unset, str]):
        auth_type (Union[None, Unset, str]):
        object_type (Union[None, Unset, str]):
        object_id (Union[None, Unset, str]):
        http_method (Union[None, Unset, str]):
        api_endpoint (Union[None, Unset, str]):
        permission_ok (Union[None, Unset, bool]):
        resolve_type (Union[None, Unset, str]):
        from_cache (Union[None, Unset, bool]):
        event_kind (Union[None, Unset, str]):
        category (Union[None, Unset, str]):
        parent_event_id (Union[None, UUID, Unset]):
        client_ip (Union[None, Unset, str]):
        user_agent (Union[None, Unset, str]):
        token_number (Union[None, Unset, int]):
        object_version (Union[None, Unset, int]):
        operation (Union[None, Unset, str]):
        subresource_type (Union[None, Unset, str]):
        subresource (Union[None, Unset, str]):
        event_id (Union[None, UUID, Unset]):
        error (Union[None, Unset, str]):
        namespace (Union[None, Unset, str]):
        search (Union[None, Unset, str]):
        from_ (Union[None, Unset, datetime.datetime]):
        to (Union[None, Unset, datetime.datetime]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        PagedAuditEventSchema
    """

    return (
        await asyncio_detailed(
            client=client,
            auth_id=auth_id,
            auth_email=auth_email,
            auth_type=auth_type,
            object_type=object_type,
            object_id=object_id,
            http_method=http_method,
            api_endpoint=api_endpoint,
            permission_ok=permission_ok,
            resolve_type=resolve_type,
            from_cache=from_cache,
            event_kind=event_kind,
            category=category,
            parent_event_id=parent_event_id,
            client_ip=client_ip,
            user_agent=user_agent,
            token_number=token_number,
            object_version=object_version,
            operation=operation,
            subresource_type=subresource_type,
            subresource=subresource,
            event_id=event_id,
            error=error,
            namespace=namespace,
            search=search,
            from_=from_,
            to=to,
            limit=limit,
            offset=offset,
        )
    ).parsed
