from typing import Any

from ninja import Body, Query, Router

from ocmoapi.oauth2_provider import oauth2_auth

from ..managers.audit import AuditManager
from ..managers.auth import AuthManager
from ..managers.namespace import NamespaceManager
from ..managers.tree import TreeManager
from ..operation_ids import (
    CREATE_CONFIG,
    GET_CONFIG_DATA_SCHEMA,
    GET_CONFIG_METADATA_SCHEMA,
    UPDATE_CONFIG,
)
from ..schemas import AnyExtendedNodeSchema, ErrorSchema
from ..schemas.metadata_json_schema import build_config_metadata_json_schema
from ..schemas.requests import ConfigDocument
from ._common import root_model_openapi_extension

router = Router()


@router.get(
    "/~config-metadata-schema",
    response=dict[str, Any],
    tags=["Config"],
    auth=oauth2_auth,
    summary="Config metadata block JSON Schema",
    operation_id=GET_CONFIG_METADATA_SCHEMA,
)
def get_config_metadata_schema(request):
    """Return JSON Schema for the top-level config metadata block (e.g. ``_ocmo``)."""
    return build_config_metadata_json_schema()


@router.get(
    "/ns/{namespace}/~config-schema/{path:path}",
    response={200: dict[str, Any], 404: ErrorSchema},
    tags=["Config"],
    auth=oauth2_auth,
    summary="Config data JSON Schema",
    operation_id=GET_CONFIG_DATA_SCHEMA,
)
def get_config_data_schema(
    request,
    namespace: str,
    path: str,
    version: str = Query("latest"),
):
    """Return JSON Schema for a config's data body, if one is defined."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    return TreeManager(ns, path, auth=auth).get_config_data_json_schema(version=version)


@router.post(
    "/ns/{namespace}/~config/~create/{path:path}",
    response={201: AnyExtendedNodeSchema, 409: ErrorSchema, 413: ErrorSchema, 422: ErrorSchema},
    tags=["Config"],
    openapi_extra=root_model_openapi_extension(ConfigDocument),
    operation_id=CREATE_CONFIG,
)
def create_config(
    request,
    namespace: str,
    path: str,
    document: ConfigDocument = Body(...),
):
    """Create a new Config at the specified path."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    item = TreeManager(ns, path, auth=auth).create_item(document.root, "config")
    return 201, item


@router.put(
    "/ns/{namespace}/~config/~update/{path:path}",
    response={200: AnyExtendedNodeSchema, 404: ErrorSchema, 413: ErrorSchema, 422: ErrorSchema},
    tags=["Config"],
    openapi_extra=root_model_openapi_extension(ConfigDocument),
    operation_id=UPDATE_CONFIG,
)
def update_config(
    request,
    namespace: str,
    path: str,
    document: ConfigDocument = Body(...),
):
    """Update an existing Config. Creates a new version only when content changes."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, path, auth=auth).update_item(document.root)
