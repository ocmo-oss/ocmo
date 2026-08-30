from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.copied_items_schema import CopiedItemsSchema
from ...models.error_schema import ErrorSchema
from ...models.location_payload import LocationPayload
from ...types import UNSET, Response, Unset


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    body: LocationPayload,
    tag_to_copy: Union[Unset, str] = "latest",
    skip_reference_validation: Union[Unset, bool] = False,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    params: Dict[str, Any] = {}

    params["tag_to_copy"] = tag_to_copy

    params["skip_reference_validation"] = skip_reference_validation

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": f"/api/v1/ns/{namespace}/~copy/{path}",
        "params": params,
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[CopiedItemsSchema, ErrorSchema]]:
    if response.status_code == 200:
        response_200 = CopiedItemsSchema.from_dict(response.json())

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
) -> Response[Union[CopiedItemsSchema, ErrorSchema]]:
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
    body: LocationPayload,
    tag_to_copy: Union[Unset, str] = "latest",
    skip_reference_validation: Union[Unset, bool] = False,
) -> Response[Union[CopiedItemsSchema, ErrorSchema]]:
    """Copy Item

     Copy an item or subtree. Only the version at tag_to_copy is copied.

    Args:
        namespace (str):
        path (str):
        tag_to_copy (Union[Unset, str]):  Default: 'latest'.
        skip_reference_validation (Union[Unset, bool]):  Default: False.
        body (LocationPayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[CopiedItemsSchema, ErrorSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        body=body,
        tag_to_copy=tag_to_copy,
        skip_reference_validation=skip_reference_validation,
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
    body: LocationPayload,
    tag_to_copy: Union[Unset, str] = "latest",
    skip_reference_validation: Union[Unset, bool] = False,
) -> Optional[Union[CopiedItemsSchema, ErrorSchema]]:
    """Copy Item

     Copy an item or subtree. Only the version at tag_to_copy is copied.

    Args:
        namespace (str):
        path (str):
        tag_to_copy (Union[Unset, str]):  Default: 'latest'.
        skip_reference_validation (Union[Unset, bool]):  Default: False.
        body (LocationPayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[CopiedItemsSchema, ErrorSchema]
    """

    return sync_detailed(
        namespace=namespace,
        path=path,
        client=client,
        body=body,
        tag_to_copy=tag_to_copy,
        skip_reference_validation=skip_reference_validation,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    body: LocationPayload,
    tag_to_copy: Union[Unset, str] = "latest",
    skip_reference_validation: Union[Unset, bool] = False,
) -> Response[Union[CopiedItemsSchema, ErrorSchema]]:
    """Copy Item

     Copy an item or subtree. Only the version at tag_to_copy is copied.

    Args:
        namespace (str):
        path (str):
        tag_to_copy (Union[Unset, str]):  Default: 'latest'.
        skip_reference_validation (Union[Unset, bool]):  Default: False.
        body (LocationPayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[CopiedItemsSchema, ErrorSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        body=body,
        tag_to_copy=tag_to_copy,
        skip_reference_validation=skip_reference_validation,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    body: LocationPayload,
    tag_to_copy: Union[Unset, str] = "latest",
    skip_reference_validation: Union[Unset, bool] = False,
) -> Optional[Union[CopiedItemsSchema, ErrorSchema]]:
    """Copy Item

     Copy an item or subtree. Only the version at tag_to_copy is copied.

    Args:
        namespace (str):
        path (str):
        tag_to_copy (Union[Unset, str]):  Default: 'latest'.
        skip_reference_validation (Union[Unset, bool]):  Default: False.
        body (LocationPayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[CopiedItemsSchema, ErrorSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            client=client,
            body=body,
            tag_to_copy=tag_to_copy,
            skip_reference_validation=skip_reference_validation,
        )
    ).parsed
