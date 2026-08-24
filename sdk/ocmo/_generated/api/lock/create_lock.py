from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_schema import ErrorSchema
from ...models.lock_payload import LockPayload
from ...models.lock_schema import LockSchema
from ...types import Response


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    body: LockPayload,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": f"/api/v1/ns/{namespace}/~lock/{path}",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorSchema, LockSchema]]:
    if response.status_code == 201:
        response_201 = LockSchema.from_dict(response.json())

        return response_201
    if response.status_code == 404:
        response_404 = ErrorSchema.from_dict(response.json())

        return response_404
    if response.status_code == 409:
        response_409 = ErrorSchema.from_dict(response.json())

        return response_409
    if response.status_code == 422:
        response_422 = ErrorSchema.from_dict(response.json())

        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ErrorSchema, LockSchema]]:
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
    body: LockPayload,
) -> Response[Union[ErrorSchema, LockSchema]]:
    """Create Lock

     Create a lock on an existing tree path. Returns 409 if already locked.

    Args:
        namespace (str):
        path (str):
        body (LockPayload): Body for creating or replacing a subtree lock.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, LockSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        body=body,
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
    body: LockPayload,
) -> Optional[Union[ErrorSchema, LockSchema]]:
    """Create Lock

     Create a lock on an existing tree path. Returns 409 if already locked.

    Args:
        namespace (str):
        path (str):
        body (LockPayload): Body for creating or replacing a subtree lock.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, LockSchema]
    """

    return sync_detailed(
        namespace=namespace,
        path=path,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    body: LockPayload,
) -> Response[Union[ErrorSchema, LockSchema]]:
    """Create Lock

     Create a lock on an existing tree path. Returns 409 if already locked.

    Args:
        namespace (str):
        path (str):
        body (LockPayload): Body for creating or replacing a subtree lock.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, LockSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    body: LockPayload,
) -> Optional[Union[ErrorSchema, LockSchema]]:
    """Create Lock

     Create a lock on an existing tree path. Returns 409 if already locked.

    Args:
        namespace (str):
        path (str):
        body (LockPayload): Body for creating or replacing a subtree lock.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, LockSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            client=client,
            body=body,
        )
    ).parsed
