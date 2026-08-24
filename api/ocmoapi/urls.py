from django.urls import path
from django.views.generic import TemplateView
from ninja import NinjaAPI

from core.api import register_exception_handlers, system
from core.api import router as core_router

from . import settings
from .auth import SwaggerOAuth2
from .oauth2_provider import oauth2_auth
from .parser import OcmoParser

api = NinjaAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs=SwaggerOAuth2(
        auth={"clientId": settings.OIDC_CLIENT_ID, "scopes": settings.OIDC_SCOPES.split(" ")},
        settings={"oauth2RedirectUrl": settings.OIDC_SWAGGER_REDIRECT_URL},
    ),
    auth=oauth2_auth,
    parser=OcmoParser(),
)

api.add_router("", system.router, auth=None)
api.add_router("/v1", core_router)

register_exception_handlers(api)


urlpatterns = [
    path(
        "api/docs/oauth2-redirect.html",
        TemplateView.as_view(
            template_name="ninja/oauth2-redirect.html",
            content_type="text/html",
        ),
    ),
    path("api/", api.urls),
]
