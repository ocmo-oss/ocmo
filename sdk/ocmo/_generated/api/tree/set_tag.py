from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.config_schema_extended import ConfigSchemaExtended
from ...models.error_schema import ErrorSchema
from ...models.info_schema import InfoSchema
from ...models.secret_schema_extended import SecretSchemaExtended
from ...models.tag_payload import TagPayload
from ...models.template_schema_extended import TemplateSchemaExtended
from ...types import Response


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    body: TagPayload,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": f"/api/v1/ns/{namespace}/~tag/{path}",
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[ErrorSchema, InfoSchema, Union["ConfigSchemaExtended", "SecretSchemaExtended", "TemplateSchemaExtended"]]
]:
    if response.status_code == 200:

        def _parse_response_200(
            data: object,
        ) -> Union["ConfigSchemaExtended", "SecretSchemaExtended", "TemplateSchemaExtended"]:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_0 = ConfigSchemaExtended.from_dict(data)

                return response_200_type_0
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_1 = TemplateSchemaExtended.from_dict(data)

                return response_200_type_1
            except:  # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            response_200_type_2 = SecretSchemaExtended.from_dict(data)

            return response_200_type_2

        response_200 = _parse_response_200(response.json())

        return response_200
    if response.status_code == 204:
        response_204 = InfoSchema.from_dict(response.json())

        return response_204
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
) -> Response[
    Union[ErrorSchema, InfoSchema, Union["ConfigSchemaExtended", "SecretSchemaExtended", "TemplateSchemaExtended"]]
]:
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
    body: TagPayload,
) -> Response[
    Union[ErrorSchema, InfoSchema, Union["ConfigSchemaExtended", "SecretSchemaExtended", "TemplateSchemaExtended"]]
]:
    """Set Tag

     Set or delete a tag on a Config, Template, or Secret.

    Args:
        namespace (str):
        path (str):
        body (TagPayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, InfoSchema, Union['ConfigSchemaExtended', 'SecretSchemaExtended', 'TemplateSchemaExtended']]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        body=body,
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
    body: TagPayload,
) -> Optional[
    Union[ErrorSchema, InfoSchema, Union["ConfigSchemaExtended", "SecretSchemaExtended", "TemplateSchemaExtended"]]
]:
    """Set Tag

     Set or delete a tag on a Config, Template, or Secret.

    Args:
        namespace (str):
        path (str):
        body (TagPayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, InfoSchema, Union['ConfigSchemaExtended', 'SecretSchemaExtended', 'TemplateSchemaExtended']]
    """

    return sync_detailed(
        namespace=namespace,
        path=path,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    body: TagPayload,
) -> Response[
    Union[ErrorSchema, InfoSchema, Union["ConfigSchemaExtended", "SecretSchemaExtended", "TemplateSchemaExtended"]]
]:
    """Set Tag

     Set or delete a tag on a Config, Template, or Secret.

    Args:
        namespace (str):
        path (str):
        body (TagPayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, InfoSchema, Union['ConfigSchemaExtended', 'SecretSchemaExtended', 'TemplateSchemaExtended']]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    body: TagPayload,
) -> Optional[
    Union[ErrorSchema, InfoSchema, Union["ConfigSchemaExtended", "SecretSchemaExtended", "TemplateSchemaExtended"]]
]:
    """Set Tag

     Set or delete a tag on a Config, Template, or Secret.

    Args:
        namespace (str):
        path (str):
        body (TagPayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, InfoSchema, Union['ConfigSchemaExtended', 'SecretSchemaExtended', 'TemplateSchemaExtended']]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            client=client,
            body=body,
        )
    ).parsed
