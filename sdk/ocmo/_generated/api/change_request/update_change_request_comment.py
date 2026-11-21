from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.change_request_comment_schema import ChangeRequestCommentSchema
from ...models.change_request_comment_update_schema import ChangeRequestCommentUpdateSchema
from ...models.error_schema import ErrorSchema
from ...types import UNSET, Response


def _get_kwargs(
    namespace: str,
    path: str,
    comment_id: int,
    *,
    body: ChangeRequestCommentUpdateSchema,
    number: int,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    params: Dict[str, Any] = {}

    params["number"] = number

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "patch",
        "url": f"/api/v1/ns/{namespace}/~change-requests/{path}/~comments/{comment_id}",
        "params": params,
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ChangeRequestCommentSchema, ErrorSchema]]:
    if response.status_code == 200:
        response_200 = ChangeRequestCommentSchema.from_dict(response.json())

        return response_200
    if response.status_code == 403:
        response_403 = ErrorSchema.from_dict(response.json())

        return response_403
    if response.status_code == 404:
        response_404 = ErrorSchema.from_dict(response.json())

        return response_404
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union[ChangeRequestCommentSchema, ErrorSchema]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    namespace: str,
    path: str,
    comment_id: int,
    *,
    client: AuthenticatedClient,
    body: ChangeRequestCommentUpdateSchema,
    number: int,
) -> Response[Union[ChangeRequestCommentSchema, ErrorSchema]]:
    """Update Change Request Comment

    Args:
        namespace (str):
        path (str):
        comment_id (int):
        number (int):
        body (ChangeRequestCommentUpdateSchema):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ChangeRequestCommentSchema, ErrorSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        comment_id=comment_id,
        body=body,
        number=number,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    namespace: str,
    path: str,
    comment_id: int,
    *,
    client: AuthenticatedClient,
    body: ChangeRequestCommentUpdateSchema,
    number: int,
) -> Optional[Union[ChangeRequestCommentSchema, ErrorSchema]]:
    """Update Change Request Comment

    Args:
        namespace (str):
        path (str):
        comment_id (int):
        number (int):
        body (ChangeRequestCommentUpdateSchema):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ChangeRequestCommentSchema, ErrorSchema]
    """

    return sync_detailed(
        namespace=namespace,
        path=path,
        comment_id=comment_id,
        client=client,
        body=body,
        number=number,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    comment_id: int,
    *,
    client: AuthenticatedClient,
    body: ChangeRequestCommentUpdateSchema,
    number: int,
) -> Response[Union[ChangeRequestCommentSchema, ErrorSchema]]:
    """Update Change Request Comment

    Args:
        namespace (str):
        path (str):
        comment_id (int):
        number (int):
        body (ChangeRequestCommentUpdateSchema):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ChangeRequestCommentSchema, ErrorSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        comment_id=comment_id,
        body=body,
        number=number,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    path: str,
    comment_id: int,
    *,
    client: AuthenticatedClient,
    body: ChangeRequestCommentUpdateSchema,
    number: int,
) -> Optional[Union[ChangeRequestCommentSchema, ErrorSchema]]:
    """Update Change Request Comment

    Args:
        namespace (str):
        path (str):
        comment_id (int):
        number (int):
        body (ChangeRequestCommentUpdateSchema):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ChangeRequestCommentSchema, ErrorSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            comment_id=comment_id,
            client=client,
            body=body,
            number=number,
        )
    ).parsed
