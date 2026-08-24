from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.product_version_with_notice_schema import ProductVersionWithNoticeSchema
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    notice: Union[Unset, bool] = False,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["notice"] = notice

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": "/api/version",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[ProductVersionWithNoticeSchema]:
    if response.status_code == 200:
        response_200 = ProductVersionWithNoticeSchema.from_dict(response.json())

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[ProductVersionWithNoticeSchema]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    notice: Union[Unset, bool] = False,
) -> Response[ProductVersionWithNoticeSchema]:
    """Application version

     Return the deployed OCMO product version and public auth configuration.

    Args:
        notice (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ProductVersionWithNoticeSchema]
    """

    kwargs = _get_kwargs(
        notice=notice,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    notice: Union[Unset, bool] = False,
) -> Optional[ProductVersionWithNoticeSchema]:
    """Application version

     Return the deployed OCMO product version and public auth configuration.

    Args:
        notice (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ProductVersionWithNoticeSchema
    """

    return sync_detailed(
        client=client,
        notice=notice,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    notice: Union[Unset, bool] = False,
) -> Response[ProductVersionWithNoticeSchema]:
    """Application version

     Return the deployed OCMO product version and public auth configuration.

    Args:
        notice (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ProductVersionWithNoticeSchema]
    """

    kwargs = _get_kwargs(
        notice=notice,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    notice: Union[Unset, bool] = False,
) -> Optional[ProductVersionWithNoticeSchema]:
    """Application version

     Return the deployed OCMO product version and public auth configuration.

    Args:
        notice (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ProductVersionWithNoticeSchema
    """

    return (
        await asyncio_detailed(
            client=client,
            notice=notice,
        )
    ).parsed
