from ninja import Query, Router

from ..managers.audit import AuditManager
from ..managers.auth import AuthManager
from ..managers.lock import LockManager
from ..managers.namespace import NamespaceManager
from ..operation_ids import (
    CREATE_LOCK,
    DELETE_LOCK,
    GET_LOCK,
    LIST_LOCKS,
    REPLACE_LOCK,
)
from ..schemas import ErrorSchema, LockSchema, LocksListSchema
from ..schemas.requests import LockPayload

router = Router()


@router.get(
    "/ns/{namespace}/~lock/",
    response={200: LocksListSchema, 404: ErrorSchema},
    tags=["Lock"],
    operation_id=LIST_LOCKS,
)
def list_locks(
    request,
    namespace: str,
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
):
    """List all active locks in the namespace."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return LockManager(ns, "*", auth=auth).list_active(limit=limit, offset=offset)


@router.get(
    "/ns/{namespace}/~lock/{path:path}",
    response={200: LockSchema, 404: ErrorSchema},
    tags=["Lock"],
    operation_id=GET_LOCK,
)
def get_lock(request, namespace: str, path: str):
    """Get lock details for a path."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return LockManager(ns, path, auth=auth).get()


@router.post(
    "/ns/{namespace}/~lock/{path:path}",
    response={201: LockSchema, 404: ErrorSchema, 409: ErrorSchema, 422: ErrorSchema},
    tags=["Lock"],
    operation_id=CREATE_LOCK,
)
def create_lock(request, namespace: str, path: str, payload: LockPayload):
    """Create a lock on an existing tree path. Returns 409 if already locked."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return 201, LockManager(ns, path, auth=auth).create(
        reason=payload.reason,
        expires_at=payload.expires_at,
    )


@router.put(
    "/ns/{namespace}/~lock/{path:path}",
    response={200: LockSchema, 404: ErrorSchema, 422: ErrorSchema},
    tags=["Lock"],
    operation_id=REPLACE_LOCK,
)
def replace_lock(request, namespace: str, path: str, payload: LockPayload):
    """Replace an existing lock (extend expiry or update reason)."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return LockManager(ns, path, auth=auth).replace(
        reason=payload.reason,
        expires_at=payload.expires_at,
    )


@router.delete(
    "/ns/{namespace}/~lock/{path:path}",
    response={204: None, 404: ErrorSchema},
    tags=["Lock"],
    operation_id=DELETE_LOCK,
)
def delete_lock(request, namespace: str, path: str):
    """Remove a lock from a path."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    LockManager(ns, path, auth=auth).delete()
    return 204, None
