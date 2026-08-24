"""Helpers for tests that need a namespace with initialized built-in configs."""

from core.managers.tree import TreeManager
from core.models import Namespace
from core.utils.namespace_special_configs import _load_builtin_schema_content

_OPEN_PERMISSIONS = """\
policies:
  - effect: Allow
    actors:
      - kind: User
        claims:
          email: "*"
    actions:
      - "*:*"
    resources:
      - "**"
"""


def create_test_namespace(name: str, description: str = "test") -> Namespace:
    """Create a namespace with a permissive ``_permissions`` config for ABAC."""
    ns = Namespace.objects.create(name=name, description=description)
    TreeManager(ns, "_permissions.schema", auth=None).create_item(
        _load_builtin_schema_content("_permissions.schema"),
        "config",
    )
    TreeManager(ns, "_permissions", auth=None).create_item(_OPEN_PERMISSIONS, "config")
    return ns
