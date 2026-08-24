"""Shared imports for tree manager mixins."""

import fnmatch
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any, Optional

import yaml
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.db.utils import IntegrityError
from django.utils import timezone

from ...constants.audit_operations import (
    OP_COPY_ITEM,
    OP_CREATE_ITEM,
    OP_DELETE_ITEM,
    OP_DELETE_TAG,
    OP_DIFF_ITEM,
    OP_LIST_VERSIONS,
    OP_MOVE_ITEM,
    OP_NAVIGATE,
    OP_PROMOTE_STABLE_TAG,
    OP_PROPAGATE_CONFIG,
    OP_ROTATE_TOKEN,
    OP_SEARCH,
    OP_SET_TAG,
    OP_UPDATE_DESCRIPTION,
    OP_UPDATE_ITEM,
)
from ...decorators import PermCheck, arg, audit, enrich_audit, require_permissions, webhook
from ...exceptions import *
from ...models import (
    Config,
    ConfigVersion,
    Folder,
    Resolver,
    Secret,
    Template,
    TemplateVersion,
    TreeItem,
)
from ...schemas import (
    ConfigOcmoMetadataSchema,
    ResolverTokenRotationResponseSchema,
    TagPayload,
    normalize_extend_ref,
)
from ...shortcuts import (
    generate_resolver_token,
    is_version_number_ref,
    parse_ref,
    resolve_relative_path,
    safe_yaml_load,
    tag_subresource_from_ref,
    validate_path_characters,
    validate_tag_name,
)
from ..audit.timeline import read_operation_for_type
from ..auth import AuthManager
from ..config_validation import ConfigDocumentParts, ConfigValidationManager
from ..crypto import CryptoManager
from ..lock import LockManager
from ..namespace import _NAMESPACE_CONFIG_ACTIVE_TAG_FIELDS
from ..propagation import PropagationManager, PropagationTargetVersion
from ..resolver_tokens import ResolverTokenManager
from ..tree_capabilities import (
    BUILTIN_NAMESPACE_CONFIG_PATHS,
    BUILTIN_NAMESPACE_PATHS,
    BUILTIN_NAMESPACE_SECRET_PATHS,
    COMPANION_SECRET_PARENT,
    TreeItemCapabilities,
    compute_tree_capabilities,
    is_builtin_namespace_config_path,
    is_builtin_namespace_path,
    normalize_tree_path,
)
from ..webhook import WebhookManager
from .constants import (
    _COPY_NODE_TYPES,
    _RESERVED_TAGS,
    TreeItemLike,
)
