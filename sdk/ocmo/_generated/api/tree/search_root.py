from http import HTTPStatus
from typing import Any, Dict, List, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_schema import ErrorSchema
from ...models.paged_tree_navigation_node_schema import PagedTreeNavigationNodeSchema
from ...types import UNSET, Response, Unset


def _get_kwargs(
    namespace: str,
    *,
    q: Union[None, Unset, str] = UNSET,
    types: Union[Unset, List[str]] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    json_q: Union[None, Unset, str]
    if isinstance(q, Unset):
        json_q = UNSET
    else:
        json_q = q
    params["q"] = json_q

    json_types: Union[Unset, List[str]] = UNSET
    if not isinstance(types, Unset):
        json_types = types

    params["types"] = json_types

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/api/v1/ns/{namespace}/~search/",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorSchema, PagedTreeNavigationNodeSchema]]:
    if response.status_code == 200:
        response_200 = PagedTreeNavigationNodeSchema.from_dict(response.json())

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
) -> Response[Union[ErrorSchema, PagedTreeNavigationNodeSchema]]:
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
    q: Union[None, Unset, str] = UNSET,
    types: Union[Unset, List[str]] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Response[Union[ErrorSchema, PagedTreeNavigationNodeSchema]]:
    """Search Root

     Search from namespace root.

    Args:
        namespace (str):
        q (Union[None, Unset, str]):
        types (Union[Unset, List[str]]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, PagedTreeNavigationNodeSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        q=q,
        types=types,
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
    q: Union[None, Unset, str] = UNSET,
    types: Union[Unset, List[str]] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Optional[Union[ErrorSchema, PagedTreeNavigationNodeSchema]]:
    """Search Root

     Search from namespace root.

    Args:
        namespace (str):
        q (Union[None, Unset, str]):
        types (Union[Unset, List[str]]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, PagedTreeNavigationNodeSchema]
    """

    return sync_detailed(
        namespace=namespace,
        client=client,
        q=q,
        types=types,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    *,
    client: AuthenticatedClient,
    q: Union[None, Unset, str] = UNSET,
    types: Union[Unset, List[str]] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Response[Union[ErrorSchema, PagedTreeNavigationNodeSchema]]:
    """Search Root

     Search from namespace root.

    Args:
        namespace (str):
        q (Union[None, Unset, str]):
        types (Union[Unset, List[str]]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, PagedTreeNavigationNodeSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        q=q,
        types=types,
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    *,
    client: AuthenticatedClient,
    q: Union[None, Unset, str] = UNSET,
    types: Union[Unset, List[str]] = UNSET,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Optional[Union[ErrorSchema, PagedTreeNavigationNodeSchema]]:
    """Search Root

     Search from namespace root.

    Args:
        namespace (str):
        q (Union[None, Unset, str]):
        types (Union[Unset, List[str]]):
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, PagedTreeNavigationNodeSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            client=client,
            q=q,
            types=types,
            limit=limit,
            offset=offset,
        )
    ).parsed
