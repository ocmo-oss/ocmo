from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.resolver_who_am_i_schema import ResolverWhoAmISchema
from ...models.user_who_am_i_schema import UserWhoAmISchema
from ...types import Response


def _get_kwargs() -> Dict[str, Any]:
    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/auth/whoami/",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union["ResolverWhoAmISchema", "UserWhoAmISchema"]]:
    if response.status_code == 200:

        def _parse_response_200(data: object) -> Union["ResolverWhoAmISchema", "UserWhoAmISchema"]:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_0 = UserWhoAmISchema.from_dict(data)

                return response_200_type_0
            except:  # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            response_200_type_1 = ResolverWhoAmISchema.from_dict(data)

            return response_200_type_1

        response_200 = _parse_response_200(response.json())

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union["ResolverWhoAmISchema", "UserWhoAmISchema"]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[Union["ResolverWhoAmISchema", "UserWhoAmISchema"]]:
    """Who Are Me

     Return information about current authenticated user or resolver.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union['ResolverWhoAmISchema', 'UserWhoAmISchema']]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
) -> Optional[Union["ResolverWhoAmISchema", "UserWhoAmISchema"]]:
    """Who Are Me

     Return information about current authenticated user or resolver.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union['ResolverWhoAmISchema', 'UserWhoAmISchema']
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
) -> Response[Union["ResolverWhoAmISchema", "UserWhoAmISchema"]]:
    """Who Are Me

     Return information about current authenticated user or resolver.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union['ResolverWhoAmISchema', 'UserWhoAmISchema']]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
) -> Optional[Union["ResolverWhoAmISchema", "UserWhoAmISchema"]]:
    """Who Are Me

     Return information about current authenticated user or resolver.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union['ResolverWhoAmISchema', 'UserWhoAmISchema']
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
