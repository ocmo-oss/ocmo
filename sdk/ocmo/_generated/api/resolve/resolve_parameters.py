from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.resolve_parameters_response_schema import ResolveParametersResponseSchema
from ...types import UNSET, Response, Unset


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    version: Union[Unset, str] = "latest",
    no_creds: Union[Unset, bool] = False,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["version"] = version

    params["no-creds"] = no_creds

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/api/v1/ns/{namespace}/~resolve-parameters/{path}",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[ResolveParametersResponseSchema]:
    if response.status_code == 200:
        response_200 = ResolveParametersResponseSchema.from_dict(response.json())

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[ResolveParametersResponseSchema]:
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
    no_creds: Union[Unset, bool] = False,
) -> Response[ResolveParametersResponseSchema]:
    """Resolve Parameters

     Return effective parameter values for a single Config (debug).

    When ``no-creds=true``, secret parameters show the dummy value
    ``<secret-value-placeholder>`` without fetching secrets (``secret:resolve``
    is not required).

    When authenticated as a Resolver, ``path`` is relative to the resolver's
    scope. Use ``'.'`` to refer to the scope root (must be a Config, not a
    folder — a folder path is rejected by the underlying resolver).

    Args:
        namespace (str):
        path (str):
        version (Union[Unset, str]):  Default: 'latest'.
        no_creds (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ResolveParametersResponseSchema]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        version=version,
        no_creds=no_creds,
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
    no_creds: Union[Unset, bool] = False,
) -> Optional[ResolveParametersResponseSchema]:
    """Resolve Parameters

     Return effective parameter values for a single Config (debug).

    When ``no-creds=true``, secret parameters show the dummy value
    ``<secret-value-placeholder>`` without fetching secrets (``secret:resolve``
    is not required).

    When authenticated as a Resolver, ``path`` is relative to the resolver's
    scope. Use ``'.'`` to refer to the scope root (must be a Config, not a
    folder — a folder path is rejected by the underlying resolver).

    Args:
        namespace (str):
        path (str):
        version (Union[Unset, str]):  Default: 'latest'.
        no_creds (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ResolveParametersResponseSchema
    """

    return sync_detailed(
        namespace=namespace,
        path=path,
        client=client,
        version=version,
        no_creds=no_creds,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    version: Union[Unset, str] = "latest",
    no_creds: Union[Unset, bool] = False,
) -> Response[ResolveParametersResponseSchema]:
    """Resolve Parameters

     Return effective parameter values for a single Config (debug).

    When ``no-creds=true``, secret parameters show the dummy value
    ``<secret-value-placeholder>`` without fetching secrets (``secret:resolve``
    is not required).

    When authenticated as a Resolver, ``path`` is relative to the resolver's
    scope. Use ``'.'`` to refer to the scope root (must be a Config, not a
    folder — a folder path is rejected by the underlying resolver).

    Args:
        namespace (str):
        path (str):
        version (Union[Unset, str]):  Default: 'latest'.
        no_creds (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ResolveParametersResponseSchema]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        version=version,
        no_creds=no_creds,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    version: Union[Unset, str] = "latest",
    no_creds: Union[Unset, bool] = False,
) -> Optional[ResolveParametersResponseSchema]:
    """Resolve Parameters

     Return effective parameter values for a single Config (debug).

    When ``no-creds=true``, secret parameters show the dummy value
    ``<secret-value-placeholder>`` without fetching secrets (``secret:resolve``
    is not required).

    When authenticated as a Resolver, ``path`` is relative to the resolver's
    scope. Use ``'.'`` to refer to the scope root (must be a Config, not a
    folder — a folder path is rejected by the underlying resolver).

    Args:
        namespace (str):
        path (str):
        version (Union[Unset, str]):  Default: 'latest'.
        no_creds (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ResolveParametersResponseSchema
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            client=client,
            version=version,
            no_creds=no_creds,
        )
    ).parsed
