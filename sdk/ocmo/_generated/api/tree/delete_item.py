from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.delete_schema import DeleteSchema
from ...models.error_schema import ErrorSchema
from ...types import UNSET, Response, Unset


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    preview: Union[Unset, bool] = True,
    version: Union[None, Unset, str] = UNSET,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["preview"] = preview

    json_version: Union[None, Unset, str]
    if isinstance(version, Unset):
        json_version = UNSET
    else:
        json_version = version
    params["version"] = json_version

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "delete",
        "url": f"/api/v1/ns/{namespace}/~delete/{path}",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[DeleteSchema, ErrorSchema]]:
    if response.status_code == 200:
        response_200 = DeleteSchema.from_dict(response.json())

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
) -> Response[Union[DeleteSchema, ErrorSchema]]:
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
    preview: Union[Unset, bool] = True,
    version: Union[None, Unset, str] = UNSET,
) -> Response[Union[DeleteSchema, ErrorSchema]]:
    """Delete Item

     Delete a tree item or a specific version. preview=true (default) is a dry run.

    Args:
        namespace (str):
        path (str):
        preview (Union[Unset, bool]):  Default: True.
        version (Union[None, Unset, str]): Soft-delete only this version (number or tag, e.g. 2 or
            stable)

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[DeleteSchema, ErrorSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        preview=preview,
        version=version,
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
    preview: Union[Unset, bool] = True,
    version: Union[None, Unset, str] = UNSET,
) -> Optional[Union[DeleteSchema, ErrorSchema]]:
    """Delete Item

     Delete a tree item or a specific version. preview=true (default) is a dry run.

    Args:
        namespace (str):
        path (str):
        preview (Union[Unset, bool]):  Default: True.
        version (Union[None, Unset, str]): Soft-delete only this version (number or tag, e.g. 2 or
            stable)

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[DeleteSchema, ErrorSchema]
    """

    return sync_detailed(
        namespace=namespace,
        path=path,
        client=client,
        preview=preview,
        version=version,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    preview: Union[Unset, bool] = True,
    version: Union[None, Unset, str] = UNSET,
) -> Response[Union[DeleteSchema, ErrorSchema]]:
    """Delete Item

     Delete a tree item or a specific version. preview=true (default) is a dry run.

    Args:
        namespace (str):
        path (str):
        preview (Union[Unset, bool]):  Default: True.
        version (Union[None, Unset, str]): Soft-delete only this version (number or tag, e.g. 2 or
            stable)

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[DeleteSchema, ErrorSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        preview=preview,
        version=version,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    preview: Union[Unset, bool] = True,
    version: Union[None, Unset, str] = UNSET,
) -> Optional[Union[DeleteSchema, ErrorSchema]]:
    """Delete Item

     Delete a tree item or a specific version. preview=true (default) is a dry run.

    Args:
        namespace (str):
        path (str):
        preview (Union[Unset, bool]):  Default: True.
        version (Union[None, Unset, str]): Soft-delete only this version (number or tag, e.g. 2 or
            stable)

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[DeleteSchema, ErrorSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            client=client,
            preview=preview,
            version=version,
        )
    ).parsed
