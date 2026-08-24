from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_schema import ErrorSchema
from ...models.global_permission_rule_payload import GlobalPermissionRulePayload
from ...models.global_permission_rule_schema import GlobalPermissionRuleSchema
from ...types import Response


def _get_kwargs(
    rule_id: str,
    *,
    body: GlobalPermissionRulePayload,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "put",
        "url": f"/api/v1/global-permissions/{rule_id}",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union[ErrorSchema, GlobalPermissionRuleSchema]]:
    if response.status_code == 200:
        response_200 = GlobalPermissionRuleSchema.from_dict(response.json())

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
) -> Response[Union[ErrorSchema, GlobalPermissionRuleSchema]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    rule_id: str,
    *,
    client: AuthenticatedClient,
    body: GlobalPermissionRulePayload,
) -> Response[Union[ErrorSchema, GlobalPermissionRuleSchema]]:
    """Update Global Permission

     Replace a Global Permission rule.

    Args:
        rule_id (str):
        body (GlobalPermissionRulePayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, GlobalPermissionRuleSchema]]
    """

    kwargs = _get_kwargs(
        rule_id=rule_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    rule_id: str,
    *,
    client: AuthenticatedClient,
    body: GlobalPermissionRulePayload,
) -> Optional[Union[ErrorSchema, GlobalPermissionRuleSchema]]:
    """Update Global Permission

     Replace a Global Permission rule.

    Args:
        rule_id (str):
        body (GlobalPermissionRulePayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, GlobalPermissionRuleSchema]
    """

    return sync_detailed(
        rule_id=rule_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    rule_id: str,
    *,
    client: AuthenticatedClient,
    body: GlobalPermissionRulePayload,
) -> Response[Union[ErrorSchema, GlobalPermissionRuleSchema]]:
    """Update Global Permission

     Replace a Global Permission rule.

    Args:
        rule_id (str):
        body (GlobalPermissionRulePayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, GlobalPermissionRuleSchema]]
    """

    kwargs = _get_kwargs(
        rule_id=rule_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    rule_id: str,
    *,
    client: AuthenticatedClient,
    body: GlobalPermissionRulePayload,
) -> Optional[Union[ErrorSchema, GlobalPermissionRuleSchema]]:
    """Update Global Permission

     Replace a Global Permission rule.

    Args:
        rule_id (str):
        body (GlobalPermissionRulePayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, GlobalPermissionRuleSchema]
    """

    return (
        await asyncio_detailed(
            rule_id=rule_id,
            client=client,
            body=body,
        )
    ).parsed
