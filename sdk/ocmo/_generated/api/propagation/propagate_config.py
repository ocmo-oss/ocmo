from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_schema import ErrorSchema
from ...models.propagation_result_schema import PropagationResultSchema
from ...types import UNSET, Response, Unset


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    version: Union[Unset, str] = "latest",
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["version"] = version

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": f"/api/v1/ns/{namespace}/~propagate/{path}",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorSchema, PropagationResultSchema]]:
    if response.status_code == 200:
        response_200 = PropagationResultSchema.from_dict(response.json())

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
) -> Response[Union[ErrorSchema, PropagationResultSchema]]:
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
    version: Union[Unset, str] = "latest",
) -> Response[Union[ErrorSchema, PropagationResultSchema]]:
    """Propagate Config

     Manually trigger propagation from the config at ``path``.

    Args:
        namespace (str):
        path (str):
        version (Union[Unset, str]):  Default: 'latest'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, PropagationResultSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
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
    version: Union[Unset, str] = "latest",
) -> Optional[Union[ErrorSchema, PropagationResultSchema]]:
    """Propagate Config

     Manually trigger propagation from the config at ``path``.

    Args:
        namespace (str):
        path (str):
        version (Union[Unset, str]):  Default: 'latest'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, PropagationResultSchema]
    """

    return sync_detailed(
        namespace=namespace,
        path=path,
        client=client,
        version=version,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    version: Union[Unset, str] = "latest",
) -> Response[Union[ErrorSchema, PropagationResultSchema]]:
    """Propagate Config

     Manually trigger propagation from the config at ``path``.

    Args:
        namespace (str):
        path (str):
        version (Union[Unset, str]):  Default: 'latest'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, PropagationResultSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        version=version,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    version: Union[Unset, str] = "latest",
) -> Optional[Union[ErrorSchema, PropagationResultSchema]]:
    """Propagate Config

     Manually trigger propagation from the config at ``path``.

    Args:
        namespace (str):
        path (str):
        version (Union[Unset, str]):  Default: 'latest'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, PropagationResultSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            client=client,
            version=version,
        )
    ).parsed
