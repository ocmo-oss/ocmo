from http import HTTPStatus
from typing import Any, Dict, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.config_schema_extended import ConfigSchemaExtended
from ...models.error_schema import ErrorSchema
from ...models.folder_schema import FolderSchema
from ...models.resolver_schema import ResolverSchema
from ...models.secret_schema_extended import SecretSchemaExtended
from ...models.template_schema_extended import TemplateSchemaExtended
from ...types import File, Response


def _get_kwargs(
    namespace: str,
    path: str,
    *,
    body: Union[
        str,
        File,
    ],
) -> Dict[str, Any]:
    headers: Dict[str, Any] = {}

    _kwargs: Dict[str, Any] = {
        "method": "put",
        "url": f"/api/v1/ns/{namespace}/~secret/~update/{path}",
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
) -> Optional[
    Union[
        ErrorSchema,
        Union[
            "ConfigSchemaExtended", "FolderSchema", "ResolverSchema", "SecretSchemaExtended", "TemplateSchemaExtended"
        ],
    ]
]:
    if response.status_code == 200:

        def _parse_response_200(
            data: object,
        ) -> Union[
            "ConfigSchemaExtended", "FolderSchema", "ResolverSchema", "SecretSchemaExtended", "TemplateSchemaExtended"
        ]:
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
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_2 = SecretSchemaExtended.from_dict(data)

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
    if response.status_code == 413:
        response_413 = ErrorSchema.from_dict(response.json())

        return response_413
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
    Union[
        ErrorSchema,
        Union[
            "ConfigSchemaExtended", "FolderSchema", "ResolverSchema", "SecretSchemaExtended", "TemplateSchemaExtended"
        ],
    ]
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
    body: Union[
        str,
        File,
    ],
) -> Response[
    Union[
        ErrorSchema,
        Union[
            "ConfigSchemaExtended", "FolderSchema", "ResolverSchema", "SecretSchemaExtended", "TemplateSchemaExtended"
        ],
    ]
]:
    """Update Secret

     Update an existing Secret. A new encrypted version is created only when content differs.

    Args:
        namespace (str):
        path (str):
        body (str): Secret credential document (YAML/JSON).
        body (File):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, Union['ConfigSchemaExtended', 'FolderSchema', 'ResolverSchema', 'SecretSchemaExtended', 'TemplateSchemaExtended']]]
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
    body: Union[
        str,
        File,
    ],
) -> Optional[
    Union[
        ErrorSchema,
        Union[
            "ConfigSchemaExtended", "FolderSchema", "ResolverSchema", "SecretSchemaExtended", "TemplateSchemaExtended"
        ],
    ]
]:
    """Update Secret

     Update an existing Secret. A new encrypted version is created only when content differs.

    Args:
        namespace (str):
        path (str):
        body (str): Secret credential document (YAML/JSON).
        body (File):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, Union['ConfigSchemaExtended', 'FolderSchema', 'ResolverSchema', 'SecretSchemaExtended', 'TemplateSchemaExtended']]
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
    body: Union[
        str,
        File,
    ],
) -> Response[
    Union[
        ErrorSchema,
        Union[
            "ConfigSchemaExtended", "FolderSchema", "ResolverSchema", "SecretSchemaExtended", "TemplateSchemaExtended"
        ],
    ]
]:
    """Update Secret

     Update an existing Secret. A new encrypted version is created only when content differs.

    Args:
        namespace (str):
        path (str):
        body (str): Secret credential document (YAML/JSON).
        body (File):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ErrorSchema, Union['ConfigSchemaExtended', 'FolderSchema', 'ResolverSchema', 'SecretSchemaExtended', 'TemplateSchemaExtended']]]
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
    body: Union[
        str,
        File,
    ],
) -> Optional[
    Union[
        ErrorSchema,
        Union[
            "ConfigSchemaExtended", "FolderSchema", "ResolverSchema", "SecretSchemaExtended", "TemplateSchemaExtended"
        ],
    ]
]:
    """Update Secret

     Update an existing Secret. A new encrypted version is created only when content differs.

    Args:
        namespace (str):
        path (str):
        body (str): Secret credential document (YAML/JSON).
        body (File):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ErrorSchema, Union['ConfigSchemaExtended', 'FolderSchema', 'ResolverSchema', 'SecretSchemaExtended', 'TemplateSchemaExtended']]
    """

    return (
        await asyncio_detailed(
            namespace=namespace,
            path=path,
            client=client,
            body=body,
        )
    ).parsed
