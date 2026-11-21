from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.change_request_list_schema import ChangeRequestListSchema
from ...models.error_schema import ErrorSchema
from ...models.list_change_requests_status_type_0 import ListChangeRequestsStatusType0
from ...types import UNSET, Response, Unset


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    status: Union[ListChangeRequestsStatusType0, None, Unset] = UNSET,
    created_by: Union[None, Unset, str] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    json_status: Union[None, Unset, str]
    if isinstance(status, Unset):
        json_status = UNSET
    elif isinstance(status, ListChangeRequestsStatusType0):
        json_status = status.value
    else:
        json_status = status
    params["status"] = json_status

    json_created_by: Union[None, Unset, str]
    if isinstance(created_by, Unset):
        json_created_by = UNSET
    else:
        json_created_by = created_by
    params["created_by"] = json_created_by

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/api/v1/ns/{namespace}/~change-requests/{path}/~list/",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ChangeRequestListSchema, ErrorSchema]]:
    if response.status_code == 200:
        response_200 = ChangeRequestListSchema.from_dict(response.json())

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
) -> Response[Union[ChangeRequestListSchema, ErrorSchema]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    status: Union[ListChangeRequestsStatusType0, None, Unset] = UNSET,
    created_by: Union[None, Unset, str] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Response[Union[ChangeRequestListSchema, ErrorSchema]]:
    """List Change Requests

    Args:
        namespace (str):
        path (str):
        status (Union[ListChangeRequestsStatusType0, None, Unset]):
        created_by (Union[None, Unset, str]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ChangeRequestListSchema, ErrorSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        status=status,
        created_by=created_by,
        limit=limit,
        offset=offset,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    status: Union[ListChangeRequestsStatusType0, None, Unset] = UNSET,
    created_by: Union[None, Unset, str] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Optional[Union[ChangeRequestListSchema, ErrorSchema]]:
    """List Change Requests

    Args:
        namespace (str):
        path (str):
        status (Union[ListChangeRequestsStatusType0, None, Unset]):
        created_by (Union[None, Unset, str]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ChangeRequestListSchema, ErrorSchema]
    """

    return sync_detailed(
        namespace=namespace,
        path=path,
        client=client,
        status=status,
        created_by=created_by,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    status: Union[ListChangeRequestsStatusType0, None, Unset] = UNSET,
    created_by: Union[None, Unset, str] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Response[Union[ChangeRequestListSchema, ErrorSchema]]:
    """List Change Requests

    Args:
        namespace (str):
        path (str):
        status (Union[ListChangeRequestsStatusType0, None, Unset]):
        created_by (Union[None, Unset, str]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ChangeRequestListSchema, ErrorSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        status=status,
        created_by=created_by,
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    status: Union[ListChangeRequestsStatusType0, None, Unset] = UNSET,
    created_by: Union[None, Unset, str] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Optional[Union[ChangeRequestListSchema, ErrorSchema]]:
    """List Change Requests

    Args:
        namespace (str):
        path (str):
        status (Union[ListChangeRequestsStatusType0, None, Unset]):
        created_by (Union[None, Unset, str]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ChangeRequestListSchema, ErrorSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            client=client,
            status=status,
            created_by=created_by,
            limit=limit,
            offset=offset,
        )
    ).parsed
