import datetime
from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_schema import ErrorSchema
from ...models.resolve_series_schema import ResolveSeriesSchema
from ...types import UNSET, Response


def _get_kwargs(
    namespace: str,
    *,
    object_id: str,
    object_type: str,
    from_: datetime.datetime,
    to: datetime.datetime,
    bucket_seconds: int,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["object_id"] = object_id

    params["object_type"] = object_type

    json_from_ = from_.isoformat()
    params["from"] = json_from_

    json_to = to.isoformat()
    params["to"] = json_to

    params["bucket_seconds"] = bucket_seconds

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/api/v1/ns/{namespace}/~audit/resolve-series/",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorSchema, ResolveSeriesSchema]]:
    if response.status_code == 200:
        response_200 = ResolveSeriesSchema.from_dict(response.json())

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
) -> Response[Union[ErrorSchema, ResolveSeriesSchema]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    namespace: str,
    *,
    client: AuthenticatedClient,
    object_id: str,
    object_type: str,
    from_: datetime.datetime,
    to: datetime.datetime,
    bucket_seconds: int,
) -> Response[Union[ErrorSchema, ResolveSeriesSchema]]:
    """Namespace Audit Resolve Series

     Time-bucketed direct vs nested resolve counts for a tree object.

    Args:
        namespace (str):
        object_id (str):
        object_type (str):
        from_ (datetime.datetime):
        to (datetime.datetime):
        bucket_seconds (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, ResolveSeriesSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        object_id=object_id,
        object_type=object_type,
        from_=from_,
        to=to,
        bucket_seconds=bucket_seconds,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    namespace: str,
    *,
    client: AuthenticatedClient,
    object_id: str,
    object_type: str,
    from_: datetime.datetime,
    to: datetime.datetime,
    bucket_seconds: int,
) -> Optional[Union[ErrorSchema, ResolveSeriesSchema]]:
    """Namespace Audit Resolve Series

     Time-bucketed direct vs nested resolve counts for a tree object.

    Args:
        namespace (str):
        object_id (str):
        object_type (str):
        from_ (datetime.datetime):
        to (datetime.datetime):
        bucket_seconds (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, ResolveSeriesSchema]
    """

    return sync_detailed(
        namespace=namespace,
        client=client,
        object_id=object_id,
        object_type=object_type,
        from_=from_,
        to=to,
        bucket_seconds=bucket_seconds,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    *,
    client: AuthenticatedClient,
    object_id: str,
    object_type: str,
    from_: datetime.datetime,
    to: datetime.datetime,
    bucket_seconds: int,
) -> Response[Union[ErrorSchema, ResolveSeriesSchema]]:
    """Namespace Audit Resolve Series

     Time-bucketed direct vs nested resolve counts for a tree object.

    Args:
        namespace (str):
        object_id (str):
        object_type (str):
        from_ (datetime.datetime):
        to (datetime.datetime):
        bucket_seconds (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, ResolveSeriesSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        object_id=object_id,
        object_type=object_type,
        from_=from_,
        to=to,
        bucket_seconds=bucket_seconds,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    *,
    client: AuthenticatedClient,
    object_id: str,
    object_type: str,
    from_: datetime.datetime,
    to: datetime.datetime,
    bucket_seconds: int,
) -> Optional[Union[ErrorSchema, ResolveSeriesSchema]]:
    """Namespace Audit Resolve Series

     Time-bucketed direct vs nested resolve counts for a tree object.

    Args:
        namespace (str):
        object_id (str):
        object_type (str):
        from_ (datetime.datetime):
        to (datetime.datetime):
        bucket_seconds (int):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, ResolveSeriesSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            client=client,
            object_id=object_id,
            object_type=object_type,
            from_=from_,
            to=to,
            bucket_seconds=bucket_seconds,
        )
    ).parsed
