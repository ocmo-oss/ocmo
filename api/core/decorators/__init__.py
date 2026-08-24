"""Cross-cutting manager method decorators."""

from .audit import audit, enrich_audit
from .permissions import PermCheck, arg, require_permissions
from .webhook import webhook

__all__ = [
    "audit",
    "enrich_audit",
    "arg",
    "PermCheck",
    "require_permissions",
    "webhook",
]
