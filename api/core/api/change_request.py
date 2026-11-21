from typing import Literal

from ninja import Query, Router

from ..managers.audit import AuditManager
from ..managers.auth import AuthManager
from ..managers.change_request import ChangeRequestManager
from ..managers.namespace import NamespaceManager
from ..operation_ids import (
    APPLY_CHANGE_REQUEST,
    APPROVE_CHANGE_REQUEST,
    CREATE_CHANGE_REQUEST,
    CREATE_CHANGE_REQUEST_COMMENT,
    DELETE_CHANGE_REQUEST_COMMENT,
    DIFF_CHANGE_REQUEST,
    GET_CHANGE_REQUEST,
    LIST_CHANGE_REQUEST_COMMENTS,
    LIST_CHANGE_REQUESTS,
    PATCH_CHANGE_REQUEST_METADATA,
    REJECT_CHANGE_REQUEST,
    UNAPPROVE_CHANGE_REQUEST,
    UPDATE_CHANGE_REQUEST,
    UPDATE_CHANGE_REQUEST_COMMENT,
    WITHDRAW_CHANGE_REQUEST,
)
from ..schemas import DiffResponseSchema, ErrorSchema
from ..schemas.change_request import (
    ChangeRequestCommentCreateSchema,
    ChangeRequestCommentListSchema,
    ChangeRequestCommentSchema,
    ChangeRequestCommentUpdateSchema,
    ChangeRequestListSchema,
    ChangeRequestMetadataPatchSchema,
    ChangeRequestRejectSchema,
    ChangeRequestSchema,
)

router = Router()


# Action routes must be registered before ``/{path:path}`` so ``app/cfg/~apply`` is not captured as the path.
@router.get(
    "/ns/{namespace}/~change-requests/{path:path}/~list/",
    response={200: ChangeRequestListSchema, 404: ErrorSchema},
    tags=["Change request"],
    operation_id=LIST_CHANGE_REQUESTS,
)
def list_change_requests(
    request,
    namespace: str,
    path: str,
    status: Literal["open", "rejected", "withdrawn", "applied"] | None = Query(None),
    created_by: str | None = Query(None, max_length=512),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return ChangeRequestManager(ns, path, auth=auth).list_requests(
        status=status,
        created_by=created_by,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/ns/{namespace}/~change-requests/{path:path}/~approve/",
    response={200: ChangeRequestSchema, 404: ErrorSchema, 409: ErrorSchema},
    tags=["Change request"],
    operation_id=APPROVE_CHANGE_REQUEST,
)
def approve_change_request(request, namespace: str, path: str, number: int = Query(..., ge=1)):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return ChangeRequestManager(ns, path, auth=auth).approve(number)


@router.post(
    "/ns/{namespace}/~change-requests/{path:path}/~unapprove/",
    response={200: ChangeRequestSchema, 404: ErrorSchema, 409: ErrorSchema},
    tags=["Change request"],
    operation_id=UNAPPROVE_CHANGE_REQUEST,
)
def unapprove_change_request(request, namespace: str, path: str, number: int = Query(..., ge=1)):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return ChangeRequestManager(ns, path, auth=auth).unapprove(number)


@router.post(
    "/ns/{namespace}/~change-requests/{path:path}/~reject/",
    response={200: ChangeRequestSchema, 404: ErrorSchema, 409: ErrorSchema},
    tags=["Change request"],
    operation_id=REJECT_CHANGE_REQUEST,
)
def reject_change_request(
    request,
    namespace: str,
    path: str,
    payload: ChangeRequestRejectSchema,
    number: int = Query(..., ge=1),
):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return ChangeRequestManager(ns, path, auth=auth).reject(number, payload.reason)


@router.post(
    "/ns/{namespace}/~change-requests/{path:path}/~withdraw/",
    response={200: ChangeRequestSchema, 404: ErrorSchema, 409: ErrorSchema},
    tags=["Change request"],
    operation_id=WITHDRAW_CHANGE_REQUEST,
)
def withdraw_change_request(request, namespace: str, path: str, number: int = Query(..., ge=1)):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return ChangeRequestManager(ns, path, auth=auth).withdraw(number)


@router.post(
    "/ns/{namespace}/~change-requests/{path:path}/~apply/",
    response={200: ChangeRequestSchema, 404: ErrorSchema, 409: ErrorSchema, 423: ErrorSchema},
    tags=["Change request"],
    operation_id=APPLY_CHANGE_REQUEST,
)
def apply_change_request(request, namespace: str, path: str, number: int = Query(..., ge=1)):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return ChangeRequestManager(ns, path, auth=auth).apply(number)


@router.get(
    "/ns/{namespace}/~change-requests/{path:path}/~diff/",
    response={200: DiffResponseSchema, 404: ErrorSchema},
    tags=["Change request"],
    operation_id=DIFF_CHANGE_REQUEST,
)
def diff_change_request(
    request,
    namespace: str,
    path: str,
    number: int = Query(..., ge=1),
    against: Literal["base", "latest"] = Query("base"),
    reveal: bool = Query(False),
):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return ChangeRequestManager(ns, path, auth=auth).diff(number, against=against, reveal=reveal)


@router.patch(
    "/ns/{namespace}/~change-requests/{path:path}/~comments/{comment_id}",
    response={200: ChangeRequestCommentSchema, 403: ErrorSchema, 404: ErrorSchema},
    tags=["Change request"],
    operation_id=UPDATE_CHANGE_REQUEST_COMMENT,
)
def update_change_request_comment(
    request,
    namespace: str,
    path: str,
    comment_id: int,
    payload: ChangeRequestCommentUpdateSchema,
    number: int = Query(..., ge=1),
):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return ChangeRequestManager(ns, path, auth=auth).update_comment(
        number,
        comment_id,
        payload.body,
    )


@router.delete(
    "/ns/{namespace}/~change-requests/{path:path}/~comments/{comment_id}",
    response={204: None, 403: ErrorSchema, 404: ErrorSchema},
    tags=["Change request"],
    operation_id=DELETE_CHANGE_REQUEST_COMMENT,
)
def delete_change_request_comment(
    request,
    namespace: str,
    path: str,
    comment_id: int,
    number: int = Query(..., ge=1),
):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    ChangeRequestManager(ns, path, auth=auth).delete_comment(number, comment_id)
    return 204, None


@router.get(
    "/ns/{namespace}/~change-requests/{path:path}/~comments/",
    response={200: ChangeRequestCommentListSchema, 404: ErrorSchema},
    tags=["Change request"],
    operation_id=LIST_CHANGE_REQUEST_COMMENTS,
)
def list_change_request_comments(
    request,
    namespace: str,
    path: str,
    number: int = Query(..., ge=1),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return ChangeRequestManager(ns, path, auth=auth).list_comments(number, limit=limit, offset=offset)


@router.post(
    "/ns/{namespace}/~change-requests/{path:path}/~comments/",
    response={201: ChangeRequestCommentSchema, 404: ErrorSchema},
    tags=["Change request"],
    operation_id=CREATE_CHANGE_REQUEST_COMMENT,
)
def create_change_request_comment(
    request,
    namespace: str,
    path: str,
    payload: ChangeRequestCommentCreateSchema,
    number: int = Query(..., ge=1),
):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    anchor = payload.anchor.model_dump() if payload.anchor else None
    return 201, ChangeRequestManager(ns, path, auth=auth).add_comment(number, payload.body, anchor=anchor)


@router.get(
    "/ns/{namespace}/~change-requests/{path:path}",
    response={200: ChangeRequestSchema, 404: ErrorSchema},
    tags=["Change request"],
    operation_id=GET_CHANGE_REQUEST,
)
def get_change_request(
    request,
    namespace: str,
    path: str,
    number: int = Query(..., ge=1),
    include_content: bool = Query(False),
):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return ChangeRequestManager(ns, path, auth=auth).get_request(number, include_content=include_content)


@router.patch(
    "/ns/{namespace}/~change-requests/{path:path}",
    response={200: ChangeRequestSchema, 404: ErrorSchema, 409: ErrorSchema, 422: ErrorSchema},
    tags=["Change request"],
    operation_id=PATCH_CHANGE_REQUEST_METADATA,
)
def patch_change_request_metadata(
    request,
    namespace: str,
    path: str,
    payload: ChangeRequestMetadataPatchSchema,
    number: int = Query(..., ge=1),
):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    return ChangeRequestManager(ns, path, auth=auth).patch_metadata(
        number,
        title=payload.title,
        description=payload.description,
    )


@router.put(
    "/ns/{namespace}/~change-requests/{path:path}",
    response={200: ChangeRequestSchema, 404: ErrorSchema, 409: ErrorSchema, 422: ErrorSchema},
    tags=["Change request"],
    operation_id=UPDATE_CHANGE_REQUEST,
)
def update_change_request(
    request,
    namespace: str,
    path: str,
    number: int = Query(..., ge=1),
):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    body = request.body.decode("utf-8") if request.body else ""
    return ChangeRequestManager(ns, path, auth=auth).update(number, body)


@router.post(
    "/ns/{namespace}/~change-requests/{path:path}",
    response={201: ChangeRequestSchema, 404: ErrorSchema, 409: ErrorSchema, 422: ErrorSchema},
    tags=["Change request"],
    operation_id=CREATE_CHANGE_REQUEST,
)
def create_change_request(
    request,
    namespace: str,
    path: str,
    title: str = Query(..., min_length=1, max_length=200),
    description: str = Query("", max_length=4096),
    base_version: str | None = Query(None, max_length=64),
):
    auth = AuthManager.from_request(request)
    ns = NamespaceManager(namespace, auth=auth).get_or_raise()
    AuditManager.bind(request, auth, namespace=ns)
    body = request.body.decode("utf-8") if request.body else ""
    return 201, ChangeRequestManager(ns, path, auth=auth).create(
        body,
        title=title,
        description=description,
        base_version_ref=base_version,
    )
