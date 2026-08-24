from datetime import UTC, datetime

from ninja import Router

from ocmoapi.auth import resolver_auth
from ocmoapi.oauth2_provider import oauth2_auth

from ..managers.audit import client_ip_from_request
from ..managers.auth import AuthManager
from ..managers.namespace import NamespaceManager
from ..operation_ids import CAN_I, WHOAMI
from ..schemas import CanIRequestSchema, CanIResponseSchema, WhoAmISchema

router = Router()

_auth = [resolver_auth, oauth2_auth]


@router.get("/auth/whoami/", response=WhoAmISchema, tags=["Auth"], auth=_auth, operation_id=WHOAMI)
def who_are_me(request):
    """Return information about current authenticated user or resolver."""
    return AuthManager.from_request(request).to_whoami()


@router.post(
    "/auth/can-i/",
    response=CanIResponseSchema,
    tags=["Auth"],
    auth=_auth,
    operation_id=CAN_I,
)
def can_i(request, payload: CanIRequestSchema):
    """Probe whether the current identity may perform requested operations."""
    auth = AuthManager.from_request(request)

    namespace = None
    if payload.namespace:
        namespace = NamespaceManager(payload.namespace, auth=auth).get_or_raise()

    allowed = auth.probe_permissions(
        payload.operations,
        namespace_name=payload.namespace,
        namespace=namespace,
        resource=payload.resource,
        request_ctx={
            "time": datetime.now(UTC),
            "ip": client_ip_from_request(request),
        },
    )
    return {"allowed": allowed}
