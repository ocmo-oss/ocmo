from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_schema import ErrorSchema
from ...models.version_history_response_schema import VersionHistoryResponseSchema
from ...types import UNSET, Response, Unset


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
    q: Union[None, Unset, str] = UNSET,
    tagged_only: Union[Unset, bool] = False,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["limit"] = limit

    params["offset"] = offset

    json_q: Union[None, Unset, str]
    if isinstance(q, Unset):
        json_q = UNSET
    else:
        json_q = q
    params["q"] = json_q

    params["tagged_only"] = tagged_only

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/api/v1/ns/{namespace}/~versions/{path}",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorSchema, VersionHistoryResponseSchema]]:
    if response.status_code == 200:
        response_200 = VersionHistoryResponseSchema.from_dict(response.json())

        return response_200
    if response.status_code == 404:
        response_404 = ErrorSchema.from_dict(response.json())

        return response_404
    if response.status_code == 422:
        response_422 = ErrorSchema.from_dict(response.json())

        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ErrorSchema, VersionHistoryResponseSchema]]:
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
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
    q: Union[None, Unset, str] = UNSET,
    tagged_only: Union[Unset, bool] = False,
) -> Response[Union[ErrorSchema, VersionHistoryResponseSchema]]:
    """List Item Versions

     List all versions (metadata) for a config, template, or secret.

    Args:
        namespace (str):
        path (str):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.
        q (Union[None, Unset, str]):
        tagged_only (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, VersionHistoryResponseSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        limit=limit,
        offset=offset,
        q=q,
        tagged_only=tagged_only,
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
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
    q: Union[None, Unset, str] = UNSET,
    tagged_only: Union[Unset, bool] = False,
) -> Optional[Union[ErrorSchema, VersionHistoryResponseSchema]]:
    """List Item Versions

     List all versions (metadata) for a config, template, or secret.

    Args:
        namespace (str):
        path (str):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.
        q (Union[None, Unset, str]):
        tagged_only (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, VersionHistoryResponseSchema]
    """

    return sync_detailed(
        namespace=namespace,
        path=path,
        client=client,
        limit=limit,
        offset=offset,
        q=q,
        tagged_only=tagged_only,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
    q: Union[None, Unset, str] = UNSET,
    tagged_only: Union[Unset, bool] = False,
) -> Response[Union[ErrorSchema, VersionHistoryResponseSchema]]:
    """List Item Versions

     List all versions (metadata) for a config, template, or secret.

    Args:
        namespace (str):
        path (str):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.
        q (Union[None, Unset, str]):
        tagged_only (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, VersionHistoryResponseSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        limit=limit,
        offset=offset,
        q=q,
        tagged_only=tagged_only,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
    q: Union[None, Unset, str] = UNSET,
    tagged_only: Union[Unset, bool] = False,
) -> Optional[Union[ErrorSchema, VersionHistoryResponseSchema]]:
    """List Item Versions

     List all versions (metadata) for a config, template, or secret.

    Args:
        namespace (str):
        path (str):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.
        q (Union[None, Unset, str]):
        tagged_only (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, VersionHistoryResponseSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            client=client,
            limit=limit,
            offset=offset,
            q=q,
            tagged_only=tagged_only,
        )
    ).parsed
