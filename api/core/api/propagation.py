from ninja import Router

from ..managers.audit import AuditManager
from ..managers.auth import AuthManager
from ..managers.namespace import NamespaceManager
from ..managers.propagation import PropagationManager
from ..operation_ids import PROPAGATE_CONFIG
from ..schemas import ErrorSchema, PropagationResultSchema

router = Router()


@router.post(
    "/ns/{namespace}/~propagate/{path:path}",
    response={200: PropagationResultSchema, 404: ErrorSchema},
    tags=["Propagation"],
    operation_id=PROPAGATE_CONFIG,
)
def propagate_config(
    request,
    namespace: str,
    path: str,
    version: str = "latest",
):
    """Manually trigger propagation from the config at ``path``."""
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return PropagationManager(ns, path, auth=auth).propagate_manual(version)
