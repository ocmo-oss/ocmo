from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.diff_response_schema import DiffResponseSchema
from ...models.error_schema import ErrorSchema
from ...types import UNSET, Response, Unset


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    from_: Union[Unset, str] = "latest",
    to: Union[Unset, str] = "latest",
    to_path: Union[None, Unset, str] = UNSET,
    reveal: Union[Unset, bool] = False,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["from"] = from_

    params["to"] = to

    json_to_path: Union[None, Unset, str]
    if isinstance(to_path, Unset):
        json_to_path = UNSET
    else:
        json_to_path = to_path
    params["to_path"] = json_to_path

    params["reveal"] = reveal

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/api/v1/ns/{namespace}/~diff/{path}",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[DiffResponseSchema, ErrorSchema]]:
    if response.status_code == 200:
        response_200 = DiffResponseSchema.from_dict(response.json())

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
) -> Response[Union[DiffResponseSchema, ErrorSchema]]:
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
    from_: Union[Unset, str] = "latest",
    to: Union[Unset, str] = "latest",
    to_path: Union[None, Unset, str] = UNSET,
    reveal: Union[Unset, bool] = False,
) -> Response[Union[DiffResponseSchema, ErrorSchema]]:
    """Diff Item

     Diff two versions of the same item (?from=, ?to=) or two items (?to_path=).

    Returns both sides for client-side diff rendering. For secrets, use
    ?reveal=true to include decrypted content; otherwise decryption_required is set.

    Args:
        namespace (str):
        path (str):
        from_ (Union[Unset, str]):  Default: 'latest'.
        to (Union[Unset, str]):  Default: 'latest'.
        to_path (Union[None, Unset, str]):
        reveal (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[DiffResponseSchema, ErrorSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        from_=from_,
        to=to,
        to_path=to_path,
        reveal=reveal,
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
    from_: Union[Unset, str] = "latest",
    to: Union[Unset, str] = "latest",
    to_path: Union[None, Unset, str] = UNSET,
    reveal: Union[Unset, bool] = False,
) -> Optional[Union[DiffResponseSchema, ErrorSchema]]:
    """Diff Item

     Diff two versions of the same item (?from=, ?to=) or two items (?to_path=).

    Returns both sides for client-side diff rendering. For secrets, use
    ?reveal=true to include decrypted content; otherwise decryption_required is set.

    Args:
        namespace (str):
        path (str):
        from_ (Union[Unset, str]):  Default: 'latest'.
        to (Union[Unset, str]):  Default: 'latest'.
        to_path (Union[None, Unset, str]):
        reveal (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[DiffResponseSchema, ErrorSchema]
    """

    return sync_detailed(
        namespace=namespace,
        path=path,
        client=client,
        from_=from_,
        to=to,
        to_path=to_path,
        reveal=reveal,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    from_: Union[Unset, str] = "latest",
    to: Union[Unset, str] = "latest",
    to_path: Union[None, Unset, str] = UNSET,
    reveal: Union[Unset, bool] = False,
) -> Response[Union[DiffResponseSchema, ErrorSchema]]:
    """Diff Item

     Diff two versions of the same item (?from=, ?to=) or two items (?to_path=).

    Returns both sides for client-side diff rendering. For secrets, use
    ?reveal=true to include decrypted content; otherwise decryption_required is set.

    Args:
        namespace (str):
        path (str):
        from_ (Union[Unset, str]):  Default: 'latest'.
        to (Union[Unset, str]):  Default: 'latest'.
        to_path (Union[None, Unset, str]):
        reveal (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[DiffResponseSchema, ErrorSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        from_=from_,
        to=to,
        to_path=to_path,
        reveal=reveal,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    from_: Union[Unset, str] = "latest",
    to: Union[Unset, str] = "latest",
    to_path: Union[None, Unset, str] = UNSET,
    reveal: Union[Unset, bool] = False,
) -> Optional[Union[DiffResponseSchema, ErrorSchema]]:
    """Diff Item

     Diff two versions of the same item (?from=, ?to=) or two items (?to_path=).

    Returns both sides for client-side diff rendering. For secrets, use
    ?reveal=true to include decrypted content; otherwise decryption_required is set.

    Args:
        namespace (str):
        path (str):
        from_ (Union[Unset, str]):  Default: 'latest'.
        to (Union[Unset, str]):  Default: 'latest'.
        to_path (Union[None, Unset, str]):
        reveal (Union[Unset, bool]):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[DiffResponseSchema, ErrorSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            client=client,
            from_=from_,
            to=to,
            to_path=to_path,
            reveal=reveal,
        )
    ).parsed
