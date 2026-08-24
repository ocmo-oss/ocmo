from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.audit_event_schema import AuditEventSchema
from ...models.error_schema import ErrorSchema
from ...types import Response


def _get_kwargs(
    namespace: str,
    event_id: str,
) -> Dict[str, Any]:
    _kwargs: Dict[str, Any] = {
        "method": "get",
        "url": f"/api/v1/ns/{namespace}/~audit/{event_id}",
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[AuditEventSchema, ErrorSchema]]:
    if response.status_code == 200:
        response_200 = AuditEventSchema.from_dict(response.json())

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
) -> Response[Union[AuditEventSchema, ErrorSchema]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    namespace: str,
    event_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Union[AuditEventSchema, ErrorSchema]]:
    """Get Namespace Audit Event

     Get a single audit event within a namespace.

    Args:
        namespace (str):
        event_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[AuditEventSchema, ErrorSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        event_id=event_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    namespace: str,
    event_id: str,
    *,
    client: AuthenticatedClient,
) -> Optional[Union[AuditEventSchema, ErrorSchema]]:
    """Get Namespace Audit Event

     Get a single audit event within a namespace.

    Args:
        namespace (str):
        event_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[AuditEventSchema, ErrorSchema]
    """

    return sync_detailed(
        namespace=namespace,
        event_id=event_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    event_id: str,
    *,
    client: AuthenticatedClient,
) -> Response[Union[AuditEventSchema, ErrorSchema]]:
    """Get Namespace Audit Event

     Get a single audit event within a namespace.

    Args:
        namespace (str):
        event_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[AuditEventSchema, ErrorSchema]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        event_id=event_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    event_id: str,
    *,
    client: AuthenticatedClient,
) -> Optional[Union[AuditEventSchema, ErrorSchema]]:
    """Get Namespace Audit Event

     Get a single audit event within a namespace.

    Args:
        namespace (str):
        event_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[AuditEventSchema, ErrorSchema]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            event_id=event_id,
            client=client,
        )
    ).parsed
