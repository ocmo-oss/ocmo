from ninja import Body, Router

from ..managers.audit import AuditManager
from ..managers.auth import AuthManager
from ..managers.namespace import NamespaceManager
from ..managers.secret import SecretManager
from ..operation_ids import CREATE_SECRET, UPDATE_SECRET
from ..schemas import AnyExtendedNodeSchema, ErrorSchema
from ..schemas.requests import SecretDocument
from ._common import root_model_openapi_extension

router = Router()


@router.post(
    "/ns/{namespace}/~secret/~create/{path:path}",
    response={201: AnyExtendedNodeSchema, 409: ErrorSchema, 413: ErrorSchema, 422: ErrorSchema},
    tags=["Secret"],
    openapi_extra=root_model_openapi_extension(SecretDocument),
    operation_id=CREATE_SECRET,
)
def create_secret(
    request,
    namespace: str,
    path: str,
    document: SecretDocument = Body(...),
):
    """Create a new Secret. The document is validated as YAML then encrypted at rest."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    item = SecretManager(ns, path, auth=auth).create(document.root)
    return 201, item


@router.put(
    "/ns/{namespace}/~secret/~update/{path:path}",
    response={200: AnyExtendedNodeSchema, 404: ErrorSchema, 413: ErrorSchema, 422: ErrorSchema},
    tags=["Secret"],
    openapi_extra=root_model_openapi_extension(SecretDocument),
    operation_id=UPDATE_SECRET,
)
def update_secret(
    request,
    namespace: str,
    path: str,
    document: SecretDocument = Body(...),
):
    """Update an existing Secret. A new encrypted version is created only when content differs."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return SecretManager(ns, path, auth=auth).update(document.root)
