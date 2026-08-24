from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_schema import ErrorSchema
from ...models.paged_audit_timeline_entry_schema import PagedAuditTimelineEntrySchema
from ...types import UNSET, Response, Unset


def _get_kwargs(
    namespace: str,
    *,
    object_id: str,
    object_type: str,
    search: Union[None, Unset, str] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["object_id"] = object_id

    params["object_type"] = object_type

    json_search: Union[None, Unset, str]
    if isinstance(search, Unset):
        json_search = UNSET
    else:
        json_search = search
    params["search"] = json_search

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/api/v1/ns/{namespace}/~audit/timeline/",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorSchema, PagedAuditTimelineEntrySchema]]:
    if response.status_code == 200:
        response_200 = PagedAuditTimelineEntrySchema.from_dict(response.json())

        return response_200
    if response.status_code == 404:
        response_404 = ErrorSchema.from_dict(response.json())

        return response_404
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ErrorSchema, PagedAuditTimelineEntrySchema]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    namespace: str,
    *,
    client: AuthenticatedClient,
    object_id: str,
    object_type: str,
    search: Union[None, Unset, str] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Response[Union[ErrorSchema, PagedAuditTimelineEntrySchema]]:
    """Namespace Audit Timeline

     Item-scoped audit timeline (requires ``<object_type>:audit`` on ``object_id``).

    Args:
        namespace (str):
        object_id (str):
        object_type (str):
        search (Union[None, Unset, str]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, PagedAuditTimelineEntrySchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        object_id=object_id,
        object_type=object_type,
        search=search,
        limit=limit,
        offset=offset,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    namespace: str,
    *,
    client: AuthenticatedClient,
    object_id: str,
    object_type: str,
    search: Union[None, Unset, str] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Optional[Union[ErrorSchema, PagedAuditTimelineEntrySchema]]:
    """Namespace Audit Timeline

     Item-scoped audit timeline (requires ``<object_type>:audit`` on ``object_id``).

    Args:
        namespace (str):
        object_id (str):
        object_type (str):
        search (Union[None, Unset, str]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, PagedAuditTimelineEntrySchema]
    """

    return sync_detailed(
        namespace=namespace,
        client=client,
        object_id=object_id,
        object_type=object_type,
        search=search,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    *,
    client: AuthenticatedClient,
    object_id: str,
    object_type: str,
    search: Union[None, Unset, str] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Response[Union[ErrorSchema, PagedAuditTimelineEntrySchema]]:
    """Namespace Audit Timeline

     Item-scoped audit timeline (requires ``<object_type>:audit`` on ``object_id``).

    Args:
        namespace (str):
        object_id (str):
        object_type (str):
        search (Union[None, Unset, str]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, PagedAuditTimelineEntrySchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        object_id=object_id,
        object_type=object_type,
        search=search,
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    *,
    client: AuthenticatedClient,
    object_id: str,
    object_type: str,
    search: Union[None, Unset, str] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Optional[Union[ErrorSchema, PagedAuditTimelineEntrySchema]]:
    """Namespace Audit Timeline

     Item-scoped audit timeline (requires ``<object_type>:audit`` on ``object_id``).

    Args:
        namespace (str):
        object_id (str):
        object_type (str):
        search (Union[None, Unset, str]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, PagedAuditTimelineEntrySchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            client=client,
            object_id=object_id,
            object_type=object_type,
            search=search,
            limit=limit,
            offset=offset,
        )
    ).parsed
