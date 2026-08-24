import json

from django.core.exceptions import ValidationError as DjangoValidationError
from ninja import Router
from ninja.errors import ValidationError as InputValidationError
from pydantic import ValidationError as PydanticValidationError

from ..exceptions import (
    ActiveTagCannotBeDeleted,
    BrokenNamespace,
    CannotCast,
    CannotResolveConfig,
    ConfigExtendNotPossible,
    ConfigTagAlreadyPointsToDesiredVersion,
    ConfigTagDoesntExists,
    ConflictPathsDetected,
    FolderCannotBeExplicitlyCreated,
    InvalidCastOption,
    InvalidResolverToken,
    InvalidResolveToken,
    LockAlreadyExists,
    NamespaceActiveTagNotFound,
    NamespaceConflict,
    NotFound,
    ParameterError,
    PathLocked,
    PermissionDenied,
    PropagationNotConfigured,
    ReservedTagsCantBeSet,
    ResolverNamespaceMismatch,
    SecretParameterError,
    TemplateRenderError,
    TreeItemConflict,
    Unauthenticated,
    UnknownCastFormat,
    UnknownCastOption,
    UploadTooLarge,
    VersionNotFound,
    WrongCopyTargetException,
    WrongMoveTargetException,
)
from ..models import GlobalPermissionRule, Namespace, TreeItem, TreeLock
from . import (
    audit,
    auth,
    config,
    global_permissions,
    lock,
    namespace,
    propagation,
    resolve,
    resolver,
    secret,
    template,
    tree,
)
from .errors import (
    create_error_response,
    format_django_validation_error,
    format_ninja_validation_errors,
    format_pydantic_validation_error,
    is_response_validation_error,
)

router = Router(tags=["v1"])
router.add_router("", auth.router)
router.add_router("", namespace.router)
router.add_router("", tree.router)
router.add_router("", config.router)
router.add_router("", template.router)
router.add_router("", secret.router)
router.add_router("", resolver.router)
router.add_router("", resolve.router)
router.add_router("", global_permissions.router)
router.add_router("", lock.router)
router.add_router("", propagation.router)
router.add_router("", audit.router)


def register_exception_handlers(api):

    @api.exception_handler(TreeItem.DoesNotExist)
    @api.exception_handler(Namespace.DoesNotExist)
    @api.exception_handler(GlobalPermissionRule.DoesNotExist)
    @api.exception_handler(TreeLock.DoesNotExist)
    @api.exception_handler(VersionNotFound)
    @api.exception_handler(PropagationNotConfigured)
    @api.exception_handler(NotFound)
    def not_found_error(request, exc):
        return create_error_response(api, request, exc, str(exc), 404)

    @api.exception_handler(NamespaceConflict)
    @api.exception_handler(ConflictPathsDetected)
    @api.exception_handler(WrongMoveTargetException)
    @api.exception_handler(WrongCopyTargetException)
    @api.exception_handler(TreeItemConflict)
    @api.exception_handler(LockAlreadyExists)
    def conflict_error(request, exc):
        return create_error_response(api, request, exc, str(exc), 409)

    @api.exception_handler(PathLocked)
    def path_locked_error(request, exc):
        return create_error_response(
            api,
            request,
            exc,
            str(exc),
            423,
            lock_path=exc.lock_path,
            reason=exc.reason,
        )

    @api.exception_handler(FolderCannotBeExplicitlyCreated)
    @api.exception_handler(ReservedTagsCantBeSet)
    @api.exception_handler(ActiveTagCannotBeDeleted)
    @api.exception_handler(NamespaceActiveTagNotFound)
    @api.exception_handler(UnknownCastFormat)
    @api.exception_handler(UnknownCastOption)
    @api.exception_handler(InvalidCastOption)
    @api.exception_handler(CannotCast)
    @api.exception_handler(CannotResolveConfig)
    @api.exception_handler(ConfigExtendNotPossible)
    @api.exception_handler(ParameterError)
    @api.exception_handler(SecretParameterError)
    @api.exception_handler(TemplateRenderError)
    def unprocessable_handler(request, exc):
        return create_error_response(
            api,
            request,
            exc,
            exc.messages if hasattr(exc, "messages") else str(exc),
            422,
        )

    @api.exception_handler(InvalidResolveToken)
    def invalid_token_handler(request, exc):
        return create_error_response(api, request, exc, str(exc), 401)

    @api.exception_handler(DjangoValidationError)
    def django_validation_error(request, exc):
        return create_error_response(api, request, exc, format_django_validation_error(exc), 422)

    @api.exception_handler(ConfigTagAlreadyPointsToDesiredVersion)
    @api.exception_handler(ConfigTagDoesntExists)
    def no_changes(request, exc):
        return api.create_response(request, {"details": str(exc)}, status=204)

    @api.exception_handler(ValueError)
    def value_error_handler(request, exc):
        return create_error_response(api, request, exc, str(exc), 422)

    @api.exception_handler(json.JSONDecodeError)
    def json_decode_error_handler(request, exc):
        return create_error_response(api, request, exc, "Invalid JSON body", 400)

    @api.exception_handler(InputValidationError)
    def input_validation_errors(request, exc):
        return create_error_response(
            api,
            request,
            exc,
            format_ninja_validation_errors(exc.errors),
            422,
        )

    @api.exception_handler(PydanticValidationError)
    def pydantic_validation_error(request, exc):
        messages = format_pydantic_validation_error(exc)
        if is_response_validation_error(exc):
            return create_error_response(
                api,
                request,
                exc,
                [f"Internal response validation error: {message}" for message in messages],
                500,
            )
        return create_error_response(api, request, exc, messages, 422)

    @api.exception_handler(PermissionDenied)
    def permission_denied(request, exc):
        return create_error_response(api, request, exc, str(exc), 403)

    @api.exception_handler(Unauthenticated)
    def unauthenticated(request, exc):
        return create_error_response(api, request, exc, str(exc), 401)

    @api.exception_handler(InvalidResolverToken)
    def failed_auth(request, exc):
        return create_error_response(api, request, exc, str(exc), 401)

    @api.exception_handler(ResolverNamespaceMismatch)
    def resolver_namespace_mismatch(request, exc):
        return create_error_response(api, request, exc, str(exc), 403)

    @api.exception_handler(UploadTooLarge)
    def upload_too_large(request, exc):
        return create_error_response(api, request, exc, str(exc), 413)

    @api.exception_handler(BrokenNamespace)
    def broken_namespace(request, exc):
        return create_error_response(api, request, exc, str(exc), 500)
