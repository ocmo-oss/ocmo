from ninja import Body, Router

from ..managers.audit import AuditManager
from ..managers.auth import AuthManager
from ..managers.namespace import NamespaceManager
from ..managers.tree import TreeManager
from ..operation_ids import CREATE_TEMPLATE, UPDATE_TEMPLATE
from ..schemas import AnyExtendedNodeSchema, ErrorSchema
from ..schemas.requests import TemplateDocument
from ._common import root_model_openapi_extension

router = Router()


@router.post(
    "/ns/{namespace}/~template/~create/{path:path}",
    response={201: AnyExtendedNodeSchema, 409: ErrorSchema, 413: ErrorSchema, 422: ErrorSchema},
    tags=["Template"],
    openapi_extra=root_model_openapi_extension(TemplateDocument),
    operation_id=CREATE_TEMPLATE,
)
def create_template(
    request,
    namespace: str,
    path: str,
    document: TemplateDocument = Body(...),
):
    """Create a new Template at the specified path."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    item = TreeManager(ns, path, auth=auth).create_item(document.root, "template")
    return 201, item


@router.put(
    "/ns/{namespace}/~template/~update/{path:path}",
    response={200: AnyExtendedNodeSchema, 404: ErrorSchema, 413: ErrorSchema, 422: ErrorSchema},
    tags=["Template"],
    openapi_extra=root_model_openapi_extension(TemplateDocument),
    operation_id=UPDATE_TEMPLATE,
)
def update_template(
    request,
    namespace: str,
    path: str,
    document: TemplateDocument = Body(...),
):
    """Update an existing Template. Creates a new version only when content changes."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return TreeManager(ns, path, auth=auth).update_item(document.root)
