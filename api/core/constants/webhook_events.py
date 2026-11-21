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
    "change_request.created",
    "change_request.updated",
    "change_request.approved",
    "change_request.unapproved",
    "change_request.rejected",
    "change_request.applied",
    "change_request.comment.created",
)

WEBHOOK_PAYLOAD_PRESETS: tuple[str, ...] = (
    "ocmo",
    "generic_json",
    "slack",
    "teams",
    "discord",
)
