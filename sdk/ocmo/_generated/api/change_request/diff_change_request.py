from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.diff_change_request_against import DiffChangeRequestAgainst
from ...models.diff_response_schema import DiffResponseSchema
from ...models.error_schema import ErrorSchema
from ...types import UNSET, Response, Unset


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    number: int,
    against: Union[Unset, DiffChangeRequestAgainst] = DiffChangeRequestAgainst.BASE,
    reveal: Union[Unset, bool] = False,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}

    params["number"] = number

    json_against: Union[Unset, str] = UNSET
    if not isinstance(against, Unset):
        json_against = against.value

    params["against"] = json_against

    params["reveal"] = reveal

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/api/v1/ns/{namespace}/~change-requests/{path}/~diff/",
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
    number: int,
    against: Union[Unset, DiffChangeRequestAgainst] = DiffChangeRequestAgainst.BASE,
    reveal: Union[Unset, bool] = False,
) -> Response[Union[DiffResponseSchema, ErrorSchema]]:
    """Diff Change Request

    Args:
        namespace (str):
        path (str):
        number (int):
        against (Union[Unset, DiffChangeRequestAgainst]):  Default: DiffChangeRequestAgainst.BASE.
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
        number=number,
        against=against,
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
    number: int,
    against: Union[Unset, DiffChangeRequestAgainst] = DiffChangeRequestAgainst.BASE,
    reveal: Union[Unset, bool] = False,
) -> Optional[Union[DiffResponseSchema, ErrorSchema]]:
    """Diff Change Request

    Args:
        namespace (str):
        path (str):
        number (int):
        against (Union[Unset, DiffChangeRequestAgainst]):  Default: DiffChangeRequestAgainst.BASE.
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
        number=number,
        against=against,
        reveal=reveal,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    number: int,
    against: Union[Unset, DiffChangeRequestAgainst] = DiffChangeRequestAgainst.BASE,
    reveal: Union[Unset, bool] = False,
) -> Response[Union[DiffResponseSchema, ErrorSchema]]:
    """Diff Change Request

    Args:
        namespace (str):
        path (str):
        number (int):
        against (Union[Unset, DiffChangeRequestAgainst]):  Default: DiffChangeRequestAgainst.BASE.
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
        number=number,
        against=against,
        reveal=reveal,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    number: int,
    against: Union[Unset, DiffChangeRequestAgainst] = DiffChangeRequestAgainst.BASE,
    reveal: Union[Unset, bool] = False,
) -> Optional[Union[DiffResponseSchema, ErrorSchema]]:
    """Diff Change Request

    Args:
        namespace (str):
        path (str):
        number (int):
        against (Union[Unset, DiffChangeRequestAgainst]):  Default: DiffChangeRequestAgainst.BASE.
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
            number=number,
            against=against,
            reveal=reveal,
        )
    ).parsed
