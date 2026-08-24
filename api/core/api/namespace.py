from ninja import Query, Router
from ninja.pagination import paginate

from ..managers.audit import AuditManager
from ..managers.auth import AuthManager
from ..managers.namespace import NamespaceManager
from ..operation_ids import (
    CREATE_NAMESPACE,
    DELETE_NAMESPACE,
    LIST_NAMESPACES,
    SHOW_NAMESPACE,
    UPDATE_NAMESPACE,
)
from ..schemas import (
    ErrorSchema,
    NamespaceCreateSchema,
    NamespaceDeletedSchema,
    NamespacePatchSchema,
    NamespaceSchema,
)

router = Router()


@router.get("/ns/", response=list[NamespaceSchema], tags=["Namespace"], operation_id=LIST_NAMESPACES)
@paginate
def list_namespaces(request, name_filter: str = Query(None)):
    """List existing namespaces with optional name filter."""
    auth = AuthManager.from_request(request)
    AuditManager.bind(request, auth)
    return NamespaceManager(None, auth=auth).list(name_filter)


@router.get(
    "/ns/{namespace}",
    response={200: NamespaceSchema, 404: ErrorSchema},
    tags=["Namespace"],
    operation_id=SHOW_NAMESPACE,
)
def show_namespace(request, namespace: str):
    """Get specific namespace details."""
    auth = AuthManager.from_request(request)
    mgr = NamespaceManager(namespace, auth=auth)
    AuditManager.bind(request, auth, namespace=mgr.ns)
    return mgr.get_or_raise()


@router.post(
    "/ns/",
    response={201: NamespaceSchema, 409: ErrorSchema},
    tags=["Namespace"],
    operation_id=CREATE_NAMESPACE,
)
def create_namespace(request, payload: NamespaceCreateSchema):
    """Create a new namespace."""
    auth = AuthManager.from_request(request)
    AuditManager.bind(request, auth)
    return 201, NamespaceManager(payload.name, auth=auth).create(payload)


@router.patch(
    "/ns/{namespace}",
    response={200: NamespaceSchema, 404: ErrorSchema, 422: ErrorSchema},
    tags=["Namespace"],
    operation_id=UPDATE_NAMESPACE,
)
def update_namespace(request, namespace: str, payload: NamespacePatchSchema):
    """Update namespace metadata or active tag pointers."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return 200, NamespaceManager(namespace, auth=auth).update(payload)


@router.delete(
    "/ns/{namespace}",
    response={204: NamespaceDeletedSchema, 404: ErrorSchema},
    tags=["Namespace"],
    operation_id=DELETE_NAMESPACE,
)
def delete_namespace(request, namespace: str):
    """Delete namespace and all its contents."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return 204, NamespaceManager(namespace, auth=auth).delete()
