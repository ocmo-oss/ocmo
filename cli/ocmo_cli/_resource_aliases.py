"""Canonical resource name aliases for CLI command groups."""

from __future__ import annotations

RESOURCE_ALIASES: dict[str, list[str]] = {
    "namespace": ["ns", "namespaces"],
    "config": ["cfg", "configs"],
    "template": ["tpl", "templates"],
    "secret": ["sec", "secrets"],
    "resolver": ["rsv", "resolvers"],
    "folder": ["dir", "folders"],
    "item": [],
    "lock": ["locks"],
    "version": ["ver", "versions"],
    "audit": ["events"],
    "globalpermission": ["gp", "globalpermissions"],
    "cast": [],
    "tree": [],
    "parameters": [],
    "draft": [],
    "token": [],
}
