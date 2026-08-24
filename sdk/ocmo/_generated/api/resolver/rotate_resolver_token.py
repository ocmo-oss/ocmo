from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_schema import ErrorSchema
from ...models.resolver_rotate_token_payload import ResolverRotateTokenPayload
from ...models.resolver_token_rotation_response_schema import ResolverTokenRotationResponseSchema
from ...types import Response


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    body: ResolverRotateTokenPayload,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": f"/api/v1/ns/{namespace}/~resolver/~rotate-token/{path}",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorSchema, ResolverTokenRotationResponseSchema]]:
    if response.status_code == 200:
        response_200 = ResolverTokenRotationResponseSchema.from_dict(response.json())

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
) -> Response[Union[ErrorSchema, ResolverTokenRotationResponseSchema]]:
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
    body: ResolverRotateTokenPayload,
) -> Response[Union[ErrorSchema, ResolverTokenRotationResponseSchema]]:
    """Rotate Resolver Token

     Rotate token1 or token2 for a Resolver (token_number must be 1 or 2).

    Args:
        namespace (str):
        path (str):
        body (ResolverRotateTokenPayload): Body for resolver token rotation.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, ResolverTokenRotationResponseSchema]]
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
    body: ResolverRotateTokenPayload,
) -> Optional[Union[ErrorSchema, ResolverTokenRotationResponseSchema]]:
    """Rotate Resolver Token

     Rotate token1 or token2 for a Resolver (token_number must be 1 or 2).

    Args:
        namespace (str):
        path (str):
        body (ResolverRotateTokenPayload): Body for resolver token rotation.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, ResolverTokenRotationResponseSchema]
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
    body: ResolverRotateTokenPayload,
) -> Response[Union[ErrorSchema, ResolverTokenRotationResponseSchema]]:
    """Rotate Resolver Token

     Rotate token1 or token2 for a Resolver (token_number must be 1 or 2).

    Args:
        namespace (str):
        path (str):
        body (ResolverRotateTokenPayload): Body for resolver token rotation.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, ResolverTokenRotationResponseSchema]]
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
    body: ResolverRotateTokenPayload,
) -> Optional[Union[ErrorSchema, ResolverTokenRotationResponseSchema]]:
    """Rotate Resolver Token

     Rotate token1 or token2 for a Resolver (token_number must be 1 or 2).

    Args:
        namespace (str):
        path (str):
        body (ResolverRotateTokenPayload): Body for resolver token rotation.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, ResolverTokenRotationResponseSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            client=client,
            body=body,
        )
    ).parsed
