"""Webhook event names emitted by the API."""

from __future__ import annotations

WEBHOOK_EVENTS: tuple[str, ...] = (
    "config.created",
    "config.updated",
    "config.deleted",
    "config.tagged",
    "config.resolved",
    "resolver.created",
    "resolver.updated",
    "secret.created",
    "secret.updated",
    "secret.deleted",
    "secret.tagged",
    "secret.resolved",
    "namespace.updated",
    "lock.created",
    "lock.updated",
    "lock.deleted",
    "propagation.triggered",
)

WEBHOOK_PAYLOAD_PRESETS: tuple[str, ...] = (
    "ocmo",
    "generic_json",
    "slack",
    "teams",
    "discord",
)
