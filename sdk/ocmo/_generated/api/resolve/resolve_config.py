from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.resolve_response_schema import ResolveResponseSchema
from ...types import UNSET, Response, Unset


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    version: Union[Unset, str] = "latest",
    cast: Union[None, Unset, str] = UNSET,
    trace_only: Union[Unset, bool] = False,
    mark_stable: Union[Unset, bool] = False,
    ignore_configs_with_missing_tags: Union[Unset, bool] = False,
    no_creds: Union[Unset, bool] = False,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["version"] = version

    json_cast: Union[None, Unset, str]
    if isinstance(cast, Unset):
        json_cast = UNSET
    else:
        json_cast = cast
    params["cast"] = json_cast

    params["trace_only"] = trace_only

    params["mark-stable"] = mark_stable

    params["ignore-configs-with-missing-tags"] = ignore_configs_with_missing_tags

    params["no-creds"] = no_creds

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/api/v1/ns/{namespace}/~resolve/{path}",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[ResolveResponseSchema]:
    if response.status_code == 200:
        response_200 = ResolveResponseSchema.from_dict(response.json())

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[ResolveResponseSchema]:
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
    cast: Union[None, Unset, str] = UNSET,
    trace_only: Union[Unset, bool] = False,
    mark_stable: Union[Unset, bool] = False,
    ignore_configs_with_missing_tags: Union[Unset, bool] = False,
    no_creds: Union[Unset, bool] = False,
) -> Response[ResolveResponseSchema]:
    """Resolve Config

     Resolve a Config (or every Config under a folder path) through the
    parameters → extend → render → cast pipeline.

    When ``mark-stable=true``, advance the reserved ``stable`` tag on resolved
    Config root(s) to the version that was just resolved (Configs only).

    When ``ignore-configs-with-missing-tags=true`` and ``path`` is a folder,
    skip Configs that do not have the requested ``version`` tag or number
    instead of failing the whole folder resolve.

    When ``no-creds=true``, secret parameters are replaced with the dummy
    value ``<secret-value-placeholder>`` without fetching or decrypting secrets
    (``secret:resolve`` is not required).

    When authenticated as a Resolver, ``path`` is relative to the resolver's
    scope. Use ``'.'`` to resolve the scope root folder.

    Args:
        namespace (str):
        path (str):
        version (Union[Unset, str]):  Default: 'latest'.
        cast (Union[None, Unset, str]):
        trace_only (Union[Unset, bool]):  Default: False.
        mark_stable (Union[Unset, bool]):  Default: False.
        ignore_configs_with_missing_tags (Union[Unset, bool]):  Default: False.
        no_creds (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ResolveResponseSchema]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        version=version,
        cast=cast,
        trace_only=trace_only,
        mark_stable=mark_stable,
        ignore_configs_with_missing_tags=ignore_configs_with_missing_tags,
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
    cast: Union[None, Unset, str] = UNSET,
    trace_only: Union[Unset, bool] = False,
    mark_stable: Union[Unset, bool] = False,
    ignore_configs_with_missing_tags: Union[Unset, bool] = False,
    no_creds: Union[Unset, bool] = False,
) -> Optional[ResolveResponseSchema]:
    """Resolve Config

     Resolve a Config (or every Config under a folder path) through the
    parameters → extend → render → cast pipeline.

    When ``mark-stable=true``, advance the reserved ``stable`` tag on resolved
    Config root(s) to the version that was just resolved (Configs only).

    When ``ignore-configs-with-missing-tags=true`` and ``path`` is a folder,
    skip Configs that do not have the requested ``version`` tag or number
    instead of failing the whole folder resolve.

    When ``no-creds=true``, secret parameters are replaced with the dummy
    value ``<secret-value-placeholder>`` without fetching or decrypting secrets
    (``secret:resolve`` is not required).

    When authenticated as a Resolver, ``path`` is relative to the resolver's
    scope. Use ``'.'`` to resolve the scope root folder.

    Args:
        namespace (str):
        path (str):
        version (Union[Unset, str]):  Default: 'latest'.
        cast (Union[None, Unset, str]):
        trace_only (Union[Unset, bool]):  Default: False.
        mark_stable (Union[Unset, bool]):  Default: False.
        ignore_configs_with_missing_tags (Union[Unset, bool]):  Default: False.
        no_creds (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ResolveResponseSchema
    """

    return sync_detailed(
        namespace=namespace,
        path=path,
        client=client,
        version=version,
        cast=cast,
        trace_only=trace_only,
        mark_stable=mark_stable,
        ignore_configs_with_missing_tags=ignore_configs_with_missing_tags,
        no_creds=no_creds,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    version: Union[Unset, str] = "latest",
    cast: Union[None, Unset, str] = UNSET,
    trace_only: Union[Unset, bool] = False,
    mark_stable: Union[Unset, bool] = False,
    ignore_configs_with_missing_tags: Union[Unset, bool] = False,
    no_creds: Union[Unset, bool] = False,
) -> Response[ResolveResponseSchema]:
    """Resolve Config

     Resolve a Config (or every Config under a folder path) through the
    parameters → extend → render → cast pipeline.

    When ``mark-stable=true``, advance the reserved ``stable`` tag on resolved
    Config root(s) to the version that was just resolved (Configs only).

    When ``ignore-configs-with-missing-tags=true`` and ``path`` is a folder,
    skip Configs that do not have the requested ``version`` tag or number
    instead of failing the whole folder resolve.

    When ``no-creds=true``, secret parameters are replaced with the dummy
    value ``<secret-value-placeholder>`` without fetching or decrypting secrets
    (``secret:resolve`` is not required).

    When authenticated as a Resolver, ``path`` is relative to the resolver's
    scope. Use ``'.'`` to resolve the scope root folder.

    Args:
        namespace (str):
        path (str):
        version (Union[Unset, str]):  Default: 'latest'.
        cast (Union[None, Unset, str]):
        trace_only (Union[Unset, bool]):  Default: False.
        mark_stable (Union[Unset, bool]):  Default: False.
        ignore_configs_with_missing_tags (Union[Unset, bool]):  Default: False.
        no_creds (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ResolveResponseSchema]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        version=version,
        cast=cast,
        trace_only=trace_only,
        mark_stable=mark_stable,
        ignore_configs_with_missing_tags=ignore_configs_with_missing_tags,
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
    cast: Union[None, Unset, str] = UNSET,
    trace_only: Union[Unset, bool] = False,
    mark_stable: Union[Unset, bool] = False,
    ignore_configs_with_missing_tags: Union[Unset, bool] = False,
    no_creds: Union[Unset, bool] = False,
) -> Optional[ResolveResponseSchema]:
    """Resolve Config

     Resolve a Config (or every Config under a folder path) through the
    parameters → extend → render → cast pipeline.

    When ``mark-stable=true``, advance the reserved ``stable`` tag on resolved
    Config root(s) to the version that was just resolved (Configs only).

    When ``ignore-configs-with-missing-tags=true`` and ``path`` is a folder,
    skip Configs that do not have the requested ``version`` tag or number
    instead of failing the whole folder resolve.

    When ``no-creds=true``, secret parameters are replaced with the dummy
    value ``<secret-value-placeholder>`` without fetching or decrypting secrets
    (``secret:resolve`` is not required).

    When authenticated as a Resolver, ``path`` is relative to the resolver's
    scope. Use ``'.'`` to resolve the scope root folder.

    Args:
        namespace (str):
        path (str):
        version (Union[Unset, str]):  Default: 'latest'.
        cast (Union[None, Unset, str]):
        trace_only (Union[Unset, bool]):  Default: False.
        mark_stable (Union[Unset, bool]):  Default: False.
        ignore_configs_with_missing_tags (Union[Unset, bool]):  Default: False.
        no_creds (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ResolveResponseSchema
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            client=client,
            version=version,
            cast=cast,
            trace_only=trace_only,
            mark_stable=mark_stable,
            ignore_configs_with_missing_tags=ignore_configs_with_missing_tags,
            no_creds=no_creds,
        )
    ).parsed
