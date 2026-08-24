from typing import Any

from ninja import Body, Router

from ocmoapi.oauth2_provider import oauth2_auth

from ..managers.audit import AuditManager
from ..managers.auth import AuthManager
from ..managers.namespace import NamespaceManager
from ..managers.tree import TreeManager
from ..operation_ids import (
    CREATE_RESOLVER,
    GET_RESOLVER_CONFIGURATION_SCHEMA,
    ROTATE_RESOLVER_TOKEN,
    UPDATE_RESOLVER,
)
from ..schemas import ErrorSchema, ResolverSchema, ResolverTokenRotationResponseSchema
from ..schemas.requests import ResolverDocument, ResolverRotateTokenPayload
from ..schemas.resolver_json_schema import build_resolver_configuration_json_schema
from ._common import root_model_openapi_extension

router = Router()


@router.get(
    "/~resolver-configuration-schema",
    response=dict[str, Any],
    tags=["Resolver"],
    auth=oauth2_auth,
    summary="Resolver configuration JSON Schema",
    operation_id=GET_RESOLVER_CONFIGURATION_SCHEMA,
)
def get_resolver_configuration_schema(request):
    """Return JSON Schema for resolver configuration YAML (editor autocomplete)."""
    return build_resolver_configuration_json_schema()


@router.post(
    "/ns/{namespace}/~resolver/~create/{path:path}",
    response={201: ResolverSchema, 409: ErrorSchema, 422: ErrorSchema},
    tags=["Resolver"],
    openapi_extra=root_model_openapi_extension(ResolverDocument),
    operation_id=CREATE_RESOLVER,
)
def create_resolver(
    request,
    namespace: str,
    path: str,
    document: ResolverDocument = Body(ResolverDocument("")),
):
    """Create a new Resolver. Returns token1 in full on creation."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    item = TreeManager(ns, path, auth=auth).create_item(document.root, "resolver")
    item._reveal_token1 = True
    return 201, item


@router.put(
    "/ns/{namespace}/~resolver/~update/{path:path}",
    response={200: ResolverSchema, 404: ErrorSchema, 422: ErrorSchema},
    tags=["Resolver"],
    openapi_extra=root_model_openapi_extension(ResolverDocument),
    operation_id=UPDATE_RESOLVER,
)
def update_resolver(
    request,
    namespace: str,
    path: str,
    document: ResolverDocument = Body(ResolverDocument("")),
):
    """Update resolver configuration."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, path, auth=auth).update_item(document.root)


@router.post(
    "/ns/{namespace}/~resolver/~rotate-token/{path:path}",
    response={200: ResolverTokenRotationResponseSchema, 404: ErrorSchema, 422: ErrorSchema},
    tags=["Resolver"],
    operation_id=ROTATE_RESOLVER_TOKEN,
)
def rotate_resolver_token(
    request,
    namespace: str,
    path: str,
    payload: ResolverRotateTokenPayload,
):
    """Rotate token1 or token2 for a Resolver (token_number must be 1 or 2)."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, path, auth=auth).rotate_resolver_token(payload.token_number)
