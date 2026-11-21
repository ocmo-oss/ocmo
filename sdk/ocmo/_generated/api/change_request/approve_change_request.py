from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.change_request_schema import ChangeRequestSchema
from ...models.error_schema import ErrorSchema
from ...types import UNSET, Response


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    number: int,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["number"] = number

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": f"/api/v1/ns/{namespace}/~change-requests/{path}/~approve/",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ChangeRequestSchema, ErrorSchema]]:
    if response.status_code == 200:
        response_200 = ChangeRequestSchema.from_dict(response.json())

        return response_200
    if response.status_code == 404:
        response_404 = ErrorSchema.from_dict(response.json())

        return response_404
    if response.status_code == 409:
        response_409 = ErrorSchema.from_dict(response.json())

        return response_409
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ChangeRequestSchema, ErrorSchema]]:
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
    number: int,
) -> Response[Union[ChangeRequestSchema, ErrorSchema]]:
    """Approve Change Request

    Args:
        namespace (str):
        path (str):
        number (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ChangeRequestSchema, ErrorSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        number=number,
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
    number: int,
) -> Optional[Union[ChangeRequestSchema, ErrorSchema]]:
    """Approve Change Request

    Args:
        namespace (str):
        path (str):
        number (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ChangeRequestSchema, ErrorSchema]
    """

    return sync_detailed(
        namespace=namespace,
        path=path,
        client=client,
        number=number,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    number: int,
) -> Response[Union[ChangeRequestSchema, ErrorSchema]]:
    """Approve Change Request

    Args:
        namespace (str):
        path (str):
        number (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ChangeRequestSchema, ErrorSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        number=number,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    number: int,
) -> Optional[Union[ChangeRequestSchema, ErrorSchema]]:
    """Approve Change Request

    Args:
        namespace (str):
        path (str):
        number (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ChangeRequestSchema, ErrorSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            client=client,
            number=number,
        )
    ).parsed
