from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_schema import ErrorSchema
from ...models.namespace_deleted_schema import NamespaceDeletedSchema
from ...types import Response


def _get_kwargs(
    namespace: str,
) -> Dict[str, Any]:
    _kwargs: Dict[str, Any] = {
        "method": "delete",
        "url": f"/api/v1/ns/{namespace}",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorSchema, NamespaceDeletedSchema]]:
    if response.status_code == 204:
        response_204 = NamespaceDeletedSchema.from_dict(response.json())

        return response_204
    if response.status_code == 404:
        response_404 = ErrorSchema.from_dict(response.json())

        return response_404
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ErrorSchema, NamespaceDeletedSchema]]:
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
) -> Response[Union[ErrorSchema, NamespaceDeletedSchema]]:
    """Delete Namespace

     Delete namespace and all its contents.

    Args:
        namespace (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, NamespaceDeletedSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    namespace: str,
    *,
    client: AuthenticatedClient,
) -> Optional[Union[ErrorSchema, NamespaceDeletedSchema]]:
    """Delete Namespace

     Delete namespace and all its contents.

    Args:
        namespace (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, NamespaceDeletedSchema]
    """

    return sync_detailed(
        namespace=namespace,
        client=client,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    *,
    client: AuthenticatedClient,
) -> Response[Union[ErrorSchema, NamespaceDeletedSchema]]:
    """Delete Namespace

     Delete namespace and all its contents.

    Args:
        namespace (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, NamespaceDeletedSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    *,
    client: AuthenticatedClient,
) -> Optional[Union[ErrorSchema, NamespaceDeletedSchema]]:
    """Delete Namespace

     Delete namespace and all its contents.

    Args:
        namespace (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, NamespaceDeletedSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            client=client,
        )
    ).parsed
