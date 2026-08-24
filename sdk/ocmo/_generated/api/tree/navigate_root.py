from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_schema import ErrorSchema
from ...models.navigation_schema import NavigationSchema
from ...types import UNSET, Response, Unset


def _get_kwargs(
    namespace: str,
    *,
    recursive: Union[Unset, bool] = False,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["recursive"] = recursive

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/api/v1/ns/{namespace}/~navigate/",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorSchema, NavigationSchema]]:
    if response.status_code == 200:
        response_200 = NavigationSchema.from_dict(response.json())

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
) -> Response[Union[ErrorSchema, NavigationSchema]]:
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
    recursive: Union[Unset, bool] = False,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Response[Union[ErrorSchema, NavigationSchema]]:
    """Navigate Root

     Navigate tree from root.

    Args:
        namespace (str):
        recursive (Union[Unset, bool]):  Default: False.
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, NavigationSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        recursive=recursive,
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
    recursive: Union[Unset, bool] = False,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Optional[Union[ErrorSchema, NavigationSchema]]:
    """Navigate Root

     Navigate tree from root.

    Args:
        namespace (str):
        recursive (Union[Unset, bool]):  Default: False.
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, NavigationSchema]
    """

    return sync_detailed(
        namespace=namespace,
        client=client,
        recursive=recursive,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    *,
    client: AuthenticatedClient,
    recursive: Union[Unset, bool] = False,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Response[Union[ErrorSchema, NavigationSchema]]:
    """Navigate Root

     Navigate tree from root.

    Args:
        namespace (str):
        recursive (Union[Unset, bool]):  Default: False.
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, NavigationSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        recursive=recursive,
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    *,
    client: AuthenticatedClient,
    recursive: Union[Unset, bool] = False,
    limit: Union[Unset, int] = 100,
    offset: Union[Unset, int] = 0,
) -> Optional[Union[ErrorSchema, NavigationSchema]]:
    """Navigate Root

     Navigate tree from root.

    Args:
        namespace (str):
        recursive (Union[Unset, bool]):  Default: False.
        limit (Union[Unset, int]):  Default: 100.
        offset (Union[Unset, int]):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, NavigationSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            client=client,
            recursive=recursive,
            limit=limit,
            offset=offset,
        )
    ).parsed
