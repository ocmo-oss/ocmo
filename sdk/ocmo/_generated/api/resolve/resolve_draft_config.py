from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.resolve_response_schema import ResolveResponseSchema
from ...types import UNSET, File, Response, Unset


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    body: Union[
        str,
        File,
    ],
    cast: Union[None, Unset, str] = UNSET,
    trace_only: Union[Unset, bool] = False,
    no_creds: Union[Unset, bool] = False,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    params: Dict[str, Any] = {}

    json_cast: Union[None, Unset, str]
    if isinstance(cast, Unset):
        json_cast = UNSET
    else:
        json_cast = cast
    params["cast"] = json_cast

    params["trace_only"] = trace_only

    params["no-creds"] = no_creds

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": f"/api/v1/ns/{namespace}/~resolve-draft/{path}",
        "params": params,
    }

    if isinstance(body, str):
        _json_body = body

        _kwargs["json"] = _json_body
        headers["Content-Type"] = "application/json"
    if isinstance(body, File):
        _content_body = body.payload

        _kwargs["content"] = _content_body
        headers["Content-Type"] = "application/octet-stream"

    _kwargs["headers"] = headers
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
    body: Union[
        str,
        File,
    ],
    cast: Union[None, Unset, str] = UNSET,
    trace_only: Union[Unset, bool] = False,
    no_creds: Union[Unset, bool] = False,
) -> Response[ResolveResponseSchema]:
    """Resolve Draft Config

     Resolve unsaved draft YAML at the given path without persisting it.

    The full parameters → extend → render → cast pipeline runs against the
    submitted content. ``config:resolve`` is required on the path and all
    transitive participants. Results are returned as download URLs (same
    shape as ``GET /~resolve/{path}``). Response items use ``version=0``.

    Args:
        namespace (str):
        path (str):
        cast (Union[None, Unset, str]):
        trace_only (Union[Unset, bool]):  Default: False.
        no_creds (Union[Unset, bool]):  Default: False.
        body (str): Config YAML document.
        body (File):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ResolveResponseSchema]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        body=body,
        cast=cast,
        trace_only=trace_only,
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
    body: Union[
        str,
        File,
    ],
    cast: Union[None, Unset, str] = UNSET,
    trace_only: Union[Unset, bool] = False,
    no_creds: Union[Unset, bool] = False,
) -> Optional[ResolveResponseSchema]:
    """Resolve Draft Config

     Resolve unsaved draft YAML at the given path without persisting it.

    The full parameters → extend → render → cast pipeline runs against the
    submitted content. ``config:resolve`` is required on the path and all
    transitive participants. Results are returned as download URLs (same
    shape as ``GET /~resolve/{path}``). Response items use ``version=0``.

    Args:
        namespace (str):
        path (str):
        cast (Union[None, Unset, str]):
        trace_only (Union[Unset, bool]):  Default: False.
        no_creds (Union[Unset, bool]):  Default: False.
        body (str): Config YAML document.
        body (File):

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
        body=body,
        cast=cast,
        trace_only=trace_only,
        no_creds=no_creds,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    body: Union[
        str,
        File,
    ],
    cast: Union[None, Unset, str] = UNSET,
    trace_only: Union[Unset, bool] = False,
    no_creds: Union[Unset, bool] = False,
) -> Response[ResolveResponseSchema]:
    """Resolve Draft Config

     Resolve unsaved draft YAML at the given path without persisting it.

    The full parameters → extend → render → cast pipeline runs against the
    submitted content. ``config:resolve`` is required on the path and all
    transitive participants. Results are returned as download URLs (same
    shape as ``GET /~resolve/{path}``). Response items use ``version=0``.

    Args:
        namespace (str):
        path (str):
        cast (Union[None, Unset, str]):
        trace_only (Union[Unset, bool]):  Default: False.
        no_creds (Union[Unset, bool]):  Default: False.
        body (str): Config YAML document.
        body (File):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ResolveResponseSchema]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        body=body,
        cast=cast,
        trace_only=trace_only,
        no_creds=no_creds,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    body: Union[
        str,
        File,
    ],
    cast: Union[None, Unset, str] = UNSET,
    trace_only: Union[Unset, bool] = False,
    no_creds: Union[Unset, bool] = False,
) -> Optional[ResolveResponseSchema]:
    """Resolve Draft Config

     Resolve unsaved draft YAML at the given path without persisting it.

    The full parameters → extend → render → cast pipeline runs against the
    submitted content. ``config:resolve`` is required on the path and all
    transitive participants. Results are returned as download URLs (same
    shape as ``GET /~resolve/{path}``). Response items use ``version=0``.

    Args:
        namespace (str):
        path (str):
        cast (Union[None, Unset, str]):
        trace_only (Union[Unset, bool]):  Default: False.
        no_creds (Union[Unset, bool]):  Default: False.
        body (str): Config YAML document.
        body (File):

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
            body=body,
            cast=cast,
            trace_only=trace_only,
            no_creds=no_creds,
        )
    ).parsed
