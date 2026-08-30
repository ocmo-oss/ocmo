from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.config_schema import ConfigSchema
from ...models.error_schema import ErrorSchema
from ...models.folder_schema import FolderSchema
from ...models.location_payload import LocationPayload
from ...models.resolver_schema import ResolverSchema
from ...models.secret_schema import SecretSchema
from ...models.template_schema import TemplateSchema
from ...types import UNSET, Response, Unset


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    body: LocationPayload,
    skip_reference_validation: Union[Unset, bool] = False,
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    params: Dict[str, Any] = {}

    params["skip_reference_validation"] = skip_reference_validation

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: Dict[str, Any] = {
        "method": "post",
        "url": f"/api/v1/ns/{namespace}/~move/{path}",
        "params": params,
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[
    Union[ErrorSchema, Union["ConfigSchema", "FolderSchema", "ResolverSchema", "SecretSchema", "TemplateSchema"]]
]:
    if response.status_code == 200:

        def _parse_response_200(
            data: object,
        ) -> Union["ConfigSchema", "FolderSchema", "ResolverSchema", "SecretSchema", "TemplateSchema"]:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_0 = ConfigSchema.from_dict(data)

                return response_200_type_0
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_1 = TemplateSchema.from_dict(data)

                return response_200_type_1
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_2 = SecretSchema.from_dict(data)

                return response_200_type_2
            except:  # noqa: E722
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_3 = ResolverSchema.from_dict(data)

                return response_200_type_3
            except:  # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            response_200_type_4 = FolderSchema.from_dict(data)

            return response_200_type_4

        response_200 = _parse_response_200(response.json())

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
) -> Response[
    Union[ErrorSchema, Union["ConfigSchema", "FolderSchema", "ResolverSchema", "SecretSchema", "TemplateSchema"]]
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
    body: LocationPayload,
    skip_reference_validation: Union[Unset, bool] = False,
) -> Response[
    Union[ErrorSchema, Union["ConfigSchema", "FolderSchema", "ResolverSchema", "SecretSchema", "TemplateSchema"]]
]:
    """Move Item

     Move an item or folder subtree to a new path.

    Args:
        namespace (str):
        path (str):
        skip_reference_validation (Union[Unset, bool]):  Default: False.
        body (LocationPayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, Union['ConfigSchema', 'FolderSchema', 'ResolverSchema', 'SecretSchema', 'TemplateSchema']]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        body=body,
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
    skip_reference_validation: Union[Unset, bool] = False,
) -> Optional[
    Union[ErrorSchema, Union["ConfigSchema", "FolderSchema", "ResolverSchema", "SecretSchema", "TemplateSchema"]]
]:
    """Move Item

     Move an item or folder subtree to a new path.

    Args:
        namespace (str):
        path (str):
        skip_reference_validation (Union[Unset, bool]):  Default: False.
        body (LocationPayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, Union['ConfigSchema', 'FolderSchema', 'ResolverSchema', 'SecretSchema', 'TemplateSchema']]
    """

    return sync_detailed(
        namespace=namespace,
        path=path,
        client=client,
        body=body,
        skip_reference_validation=skip_reference_validation,
    ).parsed


async def asyncio_detailed(
    namespace: str,
    path: str,
    *,
    client: AuthenticatedClient,
    body: LocationPayload,
    skip_reference_validation: Union[Unset, bool] = False,
) -> Response[
    Union[ErrorSchema, Union["ConfigSchema", "FolderSchema", "ResolverSchema", "SecretSchema", "TemplateSchema"]]
]:
    """Move Item

     Move an item or folder subtree to a new path.

    Args:
        namespace (str):
        path (str):
        skip_reference_validation (Union[Unset, bool]):  Default: False.
        body (LocationPayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, Union['ConfigSchema', 'FolderSchema', 'ResolverSchema', 'SecretSchema', 'TemplateSchema']]]
    """

    kwargs = _get_kwargs(
        namespace=namespace,
        path=path,
        body=body,
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
    skip_reference_validation: Union[Unset, bool] = False,
) -> Optional[
    Union[ErrorSchema, Union["ConfigSchema", "FolderSchema", "ResolverSchema", "SecretSchema", "TemplateSchema"]]
]:
    """Move Item

     Move an item or folder subtree to a new path.

    Args:
        namespace (str):
        path (str):
        skip_reference_validation (Union[Unset, bool]):  Default: False.
        body (LocationPayload):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, Union['ConfigSchema', 'FolderSchema', 'ResolverSchema', 'SecretSchema', 'TemplateSchema']]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            client=client,
            body=body,
            skip_reference_validation=skip_reference_validation,
        )
    ).parsed
