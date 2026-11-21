"""Stable OpenAPI operation identifiers.

These strings are the contract between the REST API, ``ocmo-sdk``, and ``ocmo-cli``.
They MUST NOT change without a deliberate compatibility decision.

The committed registry in ``sdk/operations.yaml`` mirrors this set and documents
SDK scope and CLI mapping hints.
"""

from __future__ import annotations

# System
HEALTH = "health"
VERSION = "version"

# Auth
WHOAMI = "whoami"
CAN_I = "can_i"

# Namespace
LIST_NAMESPACES = "list_namespaces"
SHOW_NAMESPACE = "show_namespace"
CREATE_NAMESPACE = "create_namespace"
UPDATE_NAMESPACE = "update_namespace"
DELETE_NAMESPACE = "delete_namespace"

# Tree
NAVIGATE_ROOT = "navigate_root"
NAVIGATE_PATH = "navigate_path"
SEARCH_ROOT = "search_root"
SEARCH_PATH = "search_path"
LIST_ITEM_VERSIONS = "list_item_versions"
GET_ITEM = "get_item"
DIFF_ITEM = "diff_item"
DELETE_ITEM = "delete_item"
MOVE_ITEM = "move_item"
COPY_ITEM = "copy_item"
SET_TAG = "set_tag"
DESCRIBE_ITEM = "describe_item"

# Config
GET_CONFIG_METADATA_SCHEMA = "get_config_metadata_schema"
GET_CONFIG_DATA_SCHEMA = "get_config_data_schema"
CREATE_CONFIG = "create_config"
UPDATE_CONFIG = "update_config"

# Template
CREATE_TEMPLATE = "create_template"
UPDATE_TEMPLATE = "update_template"

# Secret
CREATE_SECRET = "create_secret"
UPDATE_SECRET = "update_secret"

# Resolver
GET_RESOLVER_CONFIGURATION_SCHEMA = "get_resolver_configuration_schema"
CREATE_RESOLVER = "create_resolver"
UPDATE_RESOLVER = "update_resolver"
ROTATE_RESOLVER_TOKEN = "rotate_resolver_token"
ENABLE_RESOLVER = "enable_resolver"
DISABLE_RESOLVER = "disable_resolver"

# Resolve
LIST_CAST_FORMATS = "list_cast_formats"
DOWNLOAD_RESOLVED_ARTIFACT = "download_resolved_artifact"
RESOLVE_CONFIG = "resolve_config"
RESOLVE_PARAMETERS = "resolve_parameters"
RESOLVE_DRAFT_CONFIG = "resolve_draft_config"

# Global permissions
LIST_GLOBAL_PERMISSIONS = "list_global_permissions"
CREATE_GLOBAL_PERMISSION = "create_global_permission"
GET_GLOBAL_PERMISSION = "get_global_permission"
UPDATE_GLOBAL_PERMISSION = "update_global_permission"
DELETE_GLOBAL_PERMISSION = "delete_global_permission"
MOVE_GLOBAL_PERMISSION = "move_global_permission"

# Audit
LIST_GLOBAL_AUDIT = "list_global_audit"
GET_GLOBAL_AUDIT_EVENT = "get_global_audit_event"
LIST_NAMESPACE_AUDIT = "list_namespace_audit"
GET_NAMESPACE_AUDIT_EVENT = "get_namespace_audit_event"
NAMESPACE_AUDIT_TIMELINE = "namespace_audit_timeline"
NAMESPACE_AUDIT_RESOLVE_SERIES = "namespace_audit_resolve_series"

# Lock
LIST_LOCKS = "list_locks"
GET_LOCK = "get_lock"
CREATE_LOCK = "create_lock"
REPLACE_LOCK = "replace_lock"
DELETE_LOCK = "delete_lock"

# Propagation
PROPAGATE_CONFIG = "propagate_config"

# Change requests
LIST_CHANGE_REQUESTS = "list_change_requests"
CREATE_CHANGE_REQUEST = "create_change_request"
GET_CHANGE_REQUEST = "get_change_request"
UPDATE_CHANGE_REQUEST = "update_change_request"
PATCH_CHANGE_REQUEST_METADATA = "patch_change_request_metadata"
APPROVE_CHANGE_REQUEST = "approve_change_request"
UNAPPROVE_CHANGE_REQUEST = "unapprove_change_request"
REJECT_CHANGE_REQUEST = "reject_change_request"
WITHDRAW_CHANGE_REQUEST = "withdraw_change_request"
APPLY_CHANGE_REQUEST = "apply_change_request"
DIFF_CHANGE_REQUEST = "diff_change_request"
LIST_CHANGE_REQUEST_COMMENTS = "list_change_request_comments"
CREATE_CHANGE_REQUEST_COMMENT = "create_change_request_comment"
UPDATE_CHANGE_REQUEST_COMMENT = "update_change_request_comment"
DELETE_CHANGE_REQUEST_COMMENT = "delete_change_request_comment"

ALL: frozenset[str] = frozenset(
    {
        HEALTH,
        VERSION,
        WHOAMI,
        CAN_I,
        LIST_NAMESPACES,
        SHOW_NAMESPACE,
        CREATE_NAMESPACE,
        UPDATE_NAMESPACE,
        DELETE_NAMESPACE,
        NAVIGATE_ROOT,
        NAVIGATE_PATH,
        SEARCH_ROOT,
        SEARCH_PATH,
        LIST_ITEM_VERSIONS,
        GET_ITEM,
        DIFF_ITEM,
        DELETE_ITEM,
        MOVE_ITEM,
        COPY_ITEM,
        SET_TAG,
        DESCRIBE_ITEM,
        GET_CONFIG_METADATA_SCHEMA,
        GET_CONFIG_DATA_SCHEMA,
        CREATE_CONFIG,
        UPDATE_CONFIG,
        CREATE_TEMPLATE,
        UPDATE_TEMPLATE,
        CREATE_SECRET,
        UPDATE_SECRET,
        GET_RESOLVER_CONFIGURATION_SCHEMA,
        CREATE_RESOLVER,
        UPDATE_RESOLVER,
        ROTATE_RESOLVER_TOKEN,
        ENABLE_RESOLVER,
        DISABLE_RESOLVER,
        LIST_CAST_FORMATS,
        DOWNLOAD_RESOLVED_ARTIFACT,
        RESOLVE_CONFIG,
        RESOLVE_PARAMETERS,
        RESOLVE_DRAFT_CONFIG,
        LIST_GLOBAL_PERMISSIONS,
        CREATE_GLOBAL_PERMISSION,
        GET_GLOBAL_PERMISSION,
        UPDATE_GLOBAL_PERMISSION,
        DELETE_GLOBAL_PERMISSION,
        MOVE_GLOBAL_PERMISSION,
        LIST_GLOBAL_AUDIT,
        GET_GLOBAL_AUDIT_EVENT,
        LIST_NAMESPACE_AUDIT,
        GET_NAMESPACE_AUDIT_EVENT,
        NAMESPACE_AUDIT_TIMELINE,
        NAMESPACE_AUDIT_RESOLVE_SERIES,
        LIST_LOCKS,
        GET_LOCK,
        CREATE_LOCK,
        REPLACE_LOCK,
        DELETE_LOCK,
        PROPAGATE_CONFIG,
        LIST_CHANGE_REQUESTS,
        CREATE_CHANGE_REQUEST,
        GET_CHANGE_REQUEST,
        UPDATE_CHANGE_REQUEST,
        PATCH_CHANGE_REQUEST_METADATA,
        APPROVE_CHANGE_REQUEST,
        UNAPPROVE_CHANGE_REQUEST,
        REJECT_CHANGE_REQUEST,
        WITHDRAW_CHANGE_REQUEST,
        APPLY_CHANGE_REQUEST,
        DIFF_CHANGE_REQUEST,
        LIST_CHANGE_REQUEST_COMMENTS,
        CREATE_CHANGE_REQUEST_COMMENT,
        UPDATE_CHANGE_REQUEST_COMMENT,
        DELETE_CHANGE_REQUEST_COMMENT,
    }
)
