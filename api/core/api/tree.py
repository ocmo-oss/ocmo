from ninja import Query, Router
from ninja.pagination import paginate

from ..managers.audit import AuditManager
from ..managers.auth import AuthManager
from ..managers.namespace import NamespaceManager
from ..managers.tree import TreeManager
from ..operation_ids import (
    COPY_ITEM,
    DELETE_ITEM,
    DESCRIBE_ITEM,
    DIFF_ITEM,
    GET_ITEM,
    LIST_ITEM_VERSIONS,
    MOVE_ITEM,
    NAVIGATE_PATH,
    NAVIGATE_ROOT,
    SEARCH_PATH,
    SEARCH_ROOT,
    SET_TAG,
)
from ..schemas import (
    AnyExtendedNodeSchema,
    AnyNodeSchema,
    CopiedItemsSchema,
    DeleteSchema,
    DescribePayload,
    DiffResponseSchema,
    ErrorSchema,
    ExtendedConfigSchema,
    InfoSchema,
    LocationPayload,
    NavigationSchema,
    TagPayload,
    TreeNavigationNodeSchema,
    VersionHistoryResponseSchema,
)

router = Router()


@router.get(
    "/ns/{namespace}/~navigate/",
    response={200: NavigationSchema, 404: ErrorSchema},
    tags=["Tree"],
    operation_id=NAVIGATE_ROOT,
)
def navigate_root(
    request,
    namespace: str,
    recursive: bool = False,
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
):
    """Navigate tree from root."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, "", auth=auth).navigate(recursive=recursive, limit=limit, offset=offset)


@router.get(
    "/ns/{namespace}/~navigate/{path:path}",
    response={200: NavigationSchema, 404: ErrorSchema},
    tags=["Tree"],
    operation_id=NAVIGATE_PATH,
)
def navigate_path(
    request,
    namespace: str,
    path: str,
    recursive: bool = False,
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
):
    """Navigate tree at a specific path."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, path, auth=auth).navigate(recursive=recursive, limit=limit, offset=offset)


@router.get(
    "/ns/{namespace}/~search/",
    response={200: list[TreeNavigationNodeSchema], 404: ErrorSchema},
    tags=["Tree"],
    operation_id=SEARCH_ROOT,
)
@paginate
def search_root(request, namespace: str, q: str | None = None, types: list[str] = Query(None)):
    """Search from namespace root."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, "", auth=auth).search(query=q, node_types=types)


@router.get(
    "/ns/{namespace}/~search/{path:path}",
    response={200: list[TreeNavigationNodeSchema], 404: ErrorSchema},
    tags=["Tree"],
    operation_id=SEARCH_PATH,
)
@paginate
def search_path(request, namespace: str, path: str, q: str | None = None, types: list[str] = Query(None)):
    """Search within a subtree."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, path, auth=auth).search(query=q, node_types=types)


@router.get(
    "/ns/{namespace}/~versions/{path:path}",
    response={200: VersionHistoryResponseSchema, 404: ErrorSchema, 422: ErrorSchema},
    tags=["Tree"],
    operation_id=LIST_ITEM_VERSIONS,
)
def list_item_versions(
    request,
    namespace: str,
    path: str,
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
    tagged_only: bool = Query(False),
):
    """List all versions (metadata) for a config, template, or secret."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, path, auth=auth).list_versions(
        limit=limit,
        offset=offset,
        q=q,
        tagged_only=tagged_only,
    )


@router.get(
    "/ns/{namespace}/~get/{path:path}",
    response={200: AnyExtendedNodeSchema, 404: ErrorSchema},
    tags=["Tree"],
    operation_id=GET_ITEM,
)
def get_item(
    request,
    namespace: str,
    path: str,
    version: str = Query("latest"),
    reveal: bool = Query(False),
):
    """Get item details. For secrets, include ?reveal=true for decrypted content."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, path, auth=auth).get_extended(version=version, reveal=reveal)


@router.get(
    "/ns/{namespace}/~diff/{path:path}",
    response={200: DiffResponseSchema, 404: ErrorSchema, 422: ErrorSchema},
    tags=["Tree"],
    operation_id=DIFF_ITEM,
)
def diff_item(
    request,
    namespace: str,
    path: str,
    from_ref: str = Query("latest", alias="from"),
    to_ref: str = Query("latest", alias="to"),
    to_path: str | None = Query(None),
    reveal: bool = Query(False),
):
    """
    Diff two versions of the same item (?from=, ?to=) or two items (?to_path=).

    Returns both sides for client-side diff rendering. For secrets, use
    ?reveal=true to include decrypted content; otherwise decryption_required is set.
    """
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, path, auth=auth).diff_item(
        from_ref=from_ref,
        to_ref=to_ref,
        to_path=to_path,
        reveal=reveal,
    )


@router.delete(
    "/ns/{namespace}/~delete/{path:path}",
    response={200: DeleteSchema, 404: ErrorSchema},
    tags=["Tree"],
    operation_id=DELETE_ITEM,
)
def delete_item(
    request,
    namespace: str,
    path: str,
    preview: bool = Query(True),
    version: str | None = Query(
        None,
        description="Soft-delete only this version (number or tag, e.g. 2 or stable)",
    ),
):
    """Delete a tree item or a specific version. preview=true (default) is a dry run."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, path, auth=auth).delete_item(preview, version)


@router.post(
    "/ns/{namespace}/~move/{path:path}",
    response={200: AnyNodeSchema, 404: ErrorSchema, 409: ErrorSchema},
    tags=["Tree"],
    operation_id=MOVE_ITEM,
)
def move_item(request, namespace: str, path: str, payload: LocationPayload):
    """Move an item or folder subtree to a new path."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, path, auth=auth).move_item(payload.target_path)


@router.post(
    "/ns/{namespace}/~copy/{path:path}",
    response={200: CopiedItemsSchema, 404: ErrorSchema, 409: ErrorSchema},
    tags=["Tree"],
    operation_id=COPY_ITEM,
)
def copy_item(
    request,
    namespace: str,
    path: str,
    payload: LocationPayload,
    tag_to_copy: str = Query("latest"),
    skip_reference_validation: bool = Query(False),
):
    """Copy an item or subtree. Only the version at tag_to_copy is copied."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, path, auth=auth).copy_item(
        payload.target_path.strip("/"),
        tag_to_copy,
        validate_references=not skip_reference_validation,
    )


@router.post(
    "/ns/{namespace}/~tag/{path:path}",
    response={200: ExtendedConfigSchema, 204: InfoSchema, 404: ErrorSchema, 422: ErrorSchema},
    tags=["Tree"],
    operation_id=SET_TAG,
)
def set_tag(request, namespace: str, path: str, payload: TagPayload):
    """Set or delete a tag on a Config, Template, or Secret."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, path, auth=auth).set_item_tag(payload)


@router.post(
    "/ns/{namespace}/~describe/{path:path}",
    response={200: AnyNodeSchema, 404: ErrorSchema},
    tags=["Tree"],
    operation_id=DESCRIBE_ITEM,
)
def describe_item(request, namespace: str, path: str, payload: DescribePayload):
    """Set the Markdown description of any tree item without creating a new version."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, path, auth=auth).set_description(payload.description)
