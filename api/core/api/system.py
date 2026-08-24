import json

from django.http import HttpResponse
from ninja import Router

from ..managers.health import HealthManager
from ..managers.system import SystemManager
from ..operation_ids import HEALTH, VERSION
from ..schemas import HealthSchema, ProductVersionWithNoticeSchema

router = Router(tags=["System"])


@router.get(
    "/health",
    response={200: HealthSchema, 503: HealthSchema},
    auth=None,
    summary="Application health",
    operation_id=HEALTH,
)
def health(request):
    """Validate core dependencies required for normal API operation."""
    payload = HealthManager().check()
    status_code = 200 if payload["status"] == "ok" else 503
    return status_code, payload


@router.get(
    "/version",
    response=ProductVersionWithNoticeSchema,
    auth=None,
    summary="Application version",
    operation_id=VERSION,
)
def version(request, notice: bool = False):
    """Return the deployed OCMO product version and public auth configuration."""
    payload = SystemManager().version_payload(include_notice=notice)
    body = ProductVersionWithNoticeSchema.model_validate(payload).model_dump(
        mode="json",
        exclude_none=True,
    )
    return HttpResponse(json.dumps(body), content_type="application/json")
