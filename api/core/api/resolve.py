from django.http import HttpResponse
from ninja import Body, Query, Router

from ocmoapi.auth import resolver_auth
from ocmoapi.oauth2_provider import oauth2_auth

from ..managers.artifacts import ArtifactsManager
from ..managers.audit import AuditManager
from ..managers.auth import AuthManager
from ..managers.namespace import NamespaceManager
from ..managers.resolution import (
    ResolutionManager,
    decode_resolve_path,
    parse_query_params,
    scoped_resolve_path,
    validate_cast_format,
)
from ..managers.resolve_parameters import ResolveParametersManager
from ..managers.tree import TreeManager
from ..operation_ids import (
    DOWNLOAD_RESOLVED_ARTIFACT,
    LIST_CAST_FORMATS,
    RESOLVE_CONFIG,
    RESOLVE_DRAFT_CONFIG,
    RESOLVE_PARAMETERS,
)
from ..schemas import (
    CastFormatsListSchema,
    ResolveParametersResponseSchema,
    ResolveResponseSchema,
)
from ..schemas.cast_options import cast_format_option_schemas, format_cast_options_json_schema
from ..schemas.requests import ConfigDocument
from ..shortcuts import public_base_url
from ._common import root_model_openapi_extension

router = Router()

_resolve_auth = [resolver_auth, oauth2_auth]


@router.get(
    "/~cast-formats/",
    response=CastFormatsListSchema,
    tags=["Resolve"],
    auth=oauth2_auth,
    operation_id=LIST_CAST_FORMATS,
)
def list_cast_formats(request):
    """Return all REST-supported cast formats and their option schemas."""
    return {
        "formats": [
            {
                "format": name,
                "options_schema": format_cast_options_json_schema(name),
            }
            for name in sorted(cast_format_option_schemas())
        ],
    }


@router.get(
    "/ns/{namespace}/~resolve/{path:path}/~download/{token}",
    tags=["Resolve"],
    auth=None,
    operation_id=DOWNLOAD_RESOLVED_ARTIFACT,
)
def download_resolved_artifact(request, namespace: str, path: str, token: str):
    """Download a previously resolved artifact using a signed token.

    Request authentication is not used; the short-lived token in the URL is the
    sole credential (signed-URL semantics). Any Authorization header is ignored.
    """
    ns = NamespaceManager(namespace, auth=None).get_or_raise()
    mode, content = ArtifactsManager(ns).download_artifact(path, token)
    if mode == "xaccel":
        # X-Accel-Redirect mode: delegate to Nginx
        response = HttpResponse(status=200)
        response["X-Accel-Redirect"] = content
        response["Content-Type"] = "application/octet-stream"
        return response
    elif mode == "direct":
        return HttpResponse(content, content_type="application/octet-stream")
    else:
        raise ValueError(f"Unknown download mode: {mode}")


@router.get(
    "/ns/{namespace}/~resolve/{path:path}",
    response=ResolveResponseSchema,
    tags=["Resolve"],
    auth=_resolve_auth,
    operation_id=RESOLVE_CONFIG,
)
def resolve_config(
    request,
    namespace: str,
    path: str,
    version: str = Query("latest"),
    cast: str | None = Query(None),
    trace_only: bool = Query(False),
    mark_stable: bool = Query(False, alias="mark-stable"),
    ignore_configs_with_missing_tags: bool = Query(False, alias="ignore-configs-with-missing-tags"),
    no_creds: bool = Query(False, alias="no-creds"),
):
    """Resolve a Config (or every Config under a folder path) through the
    parameters → extend → render → cast pipeline.

    When ``mark-stable=true``, advance the reserved ``stable`` tag on resolved
    Config root(s) to the version that was just resolved (Configs only).

    When ``ignore-configs-with-missing-tags=true`` and ``path`` is a folder,
    skip Configs that do not have the requested ``version`` tag or number
    instead of failing the whole folder resolve.

    When ``no-creds=true``, secret parameters are replaced with the dummy
    value ``<secret-value-placeholder>`` without fetching or decrypting secrets
    (``secret:resolve`` is not required).

    When authenticated as a Resolver, ``path`` is relative to the resolver's
    scope. Use ``'.'`` to resolve the scope root folder.
    """
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    path = decode_resolve_path(path)
    validate_cast_format(cast)
    mgr = ResolutionManager(
        ns,
        path,
        auth=auth,
        query_params=request.GET,
        base_url=public_base_url(request),
        version=version,
        cast=cast,
        trace_only=trace_only,
        promote_stable=mark_stable,
        ignore_configs_with_missing_tags=ignore_configs_with_missing_tags,
        no_creds=no_creds,
    )
    result = mgr.resolve()
    request._resolve_cache_status = mgr.cache_status
    return result


@router.get(
    "/ns/{namespace}/~resolve-parameters/{path:path}",
    response=ResolveParametersResponseSchema,
    tags=["Resolve"],
    auth=_resolve_auth,
    operation_id=RESOLVE_PARAMETERS,
)
def resolve_parameters(
    request,
    namespace: str,
    path: str,
    version: str = Query("latest"),
    no_creds: bool = Query(False, alias="no-creds"),
):
    """Return effective parameter values for a single Config (debug).

    When ``no-creds=true``, secret parameters show the dummy value
    ``<secret-value-placeholder>`` without fetching secrets (``secret:resolve``
    is not required).

    When authenticated as a Resolver, ``path`` is relative to the resolver's
    scope. Use ``'.'`` to refer to the scope root (must be a Config, not a
    folder — a folder path is rejected by the underlying resolver).
    """
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    path = decode_resolve_path(path)
    effective_path, _ = scoped_resolve_path(ns, path, auth)
    dynamic_params, _ = parse_query_params(request.GET)
    config_obj = TreeManager(ns, effective_path, auth=auth).get_or_raise(["config"])
    rpm = ResolveParametersManager(
        ns,
        config_obj,
        base_folder="/".join(config_obj.path.split("/")[:-1]),
        version_tag=version,
        version_number=TreeManager.resolve_version(config_obj, version).version,
        dynamic_params=dynamic_params,
        auth=auth,
        no_creds=no_creds,
    )
    return rpm.resolve_debug()


@router.post(
    "/ns/{namespace}/~resolve-draft/{path:path}",
    response=ResolveResponseSchema,
    tags=["Resolve"],
    auth=[oauth2_auth],
    openapi_extra=root_model_openapi_extension(ConfigDocument),
    operation_id=RESOLVE_DRAFT_CONFIG,
)
def resolve_draft_config(
    request,
    namespace: str,
    path: str,
    document: ConfigDocument = Body(...),
    cast: str | None = Query(None),
    trace_only: bool = Query(False),
    no_creds: bool = Query(False, alias="no-creds"),
):
    """Resolve unsaved draft YAML at the given path without persisting it.

    The full parameters → extend → render → cast pipeline runs against the
    submitted content. ``config:resolve`` is required on the path and all
    transitive participants. Results are returned as download URLs (same
    shape as ``GET /~resolve/{path}``). Response items use ``version=0``.
    """
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    validate_cast_format(cast)
    mgr = ResolutionManager(
        ns,
        path,
        auth=auth,
        query_params=request.GET,
        base_url=public_base_url(request),
        cast=cast,
        trace_only=trace_only,
        no_creds=no_creds,
        draft_content=document.root,
    )
    return mgr.resolve()
