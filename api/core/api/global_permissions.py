from ninja import Query, Router

from ..managers.audit import AuditManager
from ..managers.auth import AuthManager
from ..managers.global_permissions import GlobalPermissionsManager
from ..operation_ids import (
    CREATE_GLOBAL_PERMISSION,
    DELETE_GLOBAL_PERMISSION,
    GET_GLOBAL_PERMISSION,
    LIST_GLOBAL_PERMISSIONS,
    MOVE_GLOBAL_PERMISSION,
    UPDATE_GLOBAL_PERMISSION,
)
from ..schemas import (
    ErrorSchema,
    GlobalPermissionRuleMovePayload,
    GlobalPermissionRulePayload,
    GlobalPermissionRuleSchema,
    GlobalPermissionRulesListSchema,
    InfoSchema,
)

router = Router()


@router.get(
    "/global-permissions/",
    response=GlobalPermissionRulesListSchema,
    tags=["Global Permissions"],
    operation_id=LIST_GLOBAL_PERMISSIONS,
)
def list_global_permissions(
    request,
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
):
    """Return all Global Permission rules in evaluation order."""
    auth = AuthManager.from_request(request)
    AuditManager.bind(request, auth)
    return GlobalPermissionsManager(auth=auth).list(limit=limit, offset=offset)


@router.post(
    "/global-permissions/",
    response={201: GlobalPermissionRuleSchema, 422: ErrorSchema},
    tags=["Global Permissions"],
    operation_id=CREATE_GLOBAL_PERMISSION,
)
def create_global_permission(request, payload: GlobalPermissionRulePayload):
    """Append a new Global Permission rule at the end of the ordered list."""
    auth = AuthManager.from_request(request)
    AuditManager.bind(request, auth)
    rule = GlobalPermissionsManager(auth=auth).create(payload)
    return 201, rule


@router.get(
    "/global-permissions/{rule_id}",
    response={200: GlobalPermissionRuleSchema, 404: ErrorSchema},
    tags=["Global Permissions"],
    operation_id=GET_GLOBAL_PERMISSION,
)
def get_global_permission(request, rule_id: str):
    """Get a single Global Permission rule."""
    auth = AuthManager.from_request(request)
    AuditManager.bind(request, auth)
    return GlobalPermissionsManager(auth=auth).get(rule_id)


@router.put(
    "/global-permissions/{rule_id}",
    response={200: GlobalPermissionRuleSchema, 404: ErrorSchema},
    tags=["Global Permissions"],
    operation_id=UPDATE_GLOBAL_PERMISSION,
)
def update_global_permission(request, rule_id: str, payload: GlobalPermissionRulePayload):
    """Replace a Global Permission rule."""
    auth = AuthManager.from_request(request)
    AuditManager.bind(request, auth)
    return GlobalPermissionsManager(auth=auth).update(rule_id, payload)


@router.delete(
    "/global-permissions/{rule_id}",
    response={204: InfoSchema, 404: ErrorSchema},
    tags=["Global Permissions"],
    operation_id=DELETE_GLOBAL_PERMISSION,
)
def delete_global_permission(request, rule_id: str):
    """Delete a Global Permission rule."""
    auth = AuthManager.from_request(request)
    AuditManager.bind(request, auth)
    GlobalPermissionsManager(auth=auth).delete(rule_id)
    return 204, {"details": "Rule deleted"}


@router.post(
    "/global-permissions/{rule_id}/~move/",
    response={200: GlobalPermissionRuleSchema, 404: ErrorSchema},
    tags=["Global Permissions"],
    operation_id=MOVE_GLOBAL_PERMISSION,
)
def move_global_permission(request, rule_id: str, payload: GlobalPermissionRuleMovePayload):
    """Reorder a Global Permission rule by setting a new position."""
    auth = AuthManager.from_request(request)
    AuditManager.bind(request, auth)
    return GlobalPermissionsManager(auth=auth).move(rule_id, payload.position)
