from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...types import Response


def _get_kwargs(
    namespace: str,
    path: str,
    token: str,
) -> Dict[str, Any]:
    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/api/v1/ns/{namespace}/~resolve/{path}/~download/{token}",
    }

    return _kwargs


def _parse_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Optional[Any]:
    if response.status_code == 200:
        return None
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: Union[AuthenticatedClient, Client], response: httpx.Response) -> Response[Any]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    namespace: str,
    path: str,
    token: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Any]:
    """Download Resolved Artifact

     Download a previously resolved artifact using a signed token.

    Request authentication is not used; the short-lived token in the URL is the
    sole credential (signed-URL semantics). Any Authorization header is ignored.

    Args:
        namespace (str):
        path (str):
        token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        token=token,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


async def asyncio_detailed(
    namespace: str,
    path: str,
    token: str,
    *,
    client: Union[AuthenticatedClient, Client],
) -> Response[Any]:
    """Download Resolved Artifact

     Download a previously resolved artifact using a signed token.

    Request authentication is not used; the short-lived token in the URL is the
    sole credential (signed-URL semantics). Any Authorization header is ignored.

    Args:
        namespace (str):
        path (str):
        token (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        token=token,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)
