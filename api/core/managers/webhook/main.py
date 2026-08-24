"""Namespace-scoped webhook config, payload building, and event dispatch."""

from __future__ import annotations

import fnmatch
import hashlib
import hmac
import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import requests
from django.conf import settings
from django.db import transaction

from ...schemas.webhooks import WebhookEntrySchema, WebhooksConfig
from ...shortcuts import make_template_environment
from .cache import _CachedWebhooksEntry, config_cache

logger = logging.getLogger(__name__)


@dataclass
class WebhookEvent:
    """Immutable event descriptor passed to every delivery path."""

    event: str
    namespace: str
    path: str | None
    version: int | None
    tag: str | None
    actor: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    details: dict[str, Any] | None = None


class WebhookManager:
    """Namespace-scoped webhook config, payload building, and event dispatch."""

    _config_cache = config_cache

    def __init__(self, namespace, *, auth=None) -> None:
        self.namespace = namespace
        self.auth = auth

    @staticmethod
    def invalidate(
        namespace_id: int | None = None,
        *,
        secret_path: str | None = None,
    ) -> None:
        """Drop cached resolved webhook config."""
        if namespace_id is None:
            config_cache.clear()
            return
        if secret_path is not None:
            config_cache.invalidate_namespace_secret(namespace_id, secret_path)
        else:
            config_cache.invalidate_namespace(namespace_id)

    @staticmethod
    def deliver(webhook_id: str, url: str, body: bytes, headers: dict) -> None:
        """Perform a single outbound HTTP POST. Never raises — logs failures instead."""
        timeout = getattr(settings, "OCMO_WEBHOOK_TIMEOUT_SECONDS", 5.0)
        try:
            resp = requests.post(url, data=body, headers=headers, timeout=timeout)
            if resp.ok:
                logger.info("Webhook %r delivered to %s (%d)", webhook_id, url, resp.status_code)
            else:
                logger.warning(
                    "Webhook %r delivery to %s returned HTTP %d",
                    webhook_id,
                    url,
                    resp.status_code,
                )
        except Exception as exc:
            logger.warning("Webhook %r delivery to %s failed: %s", webhook_id, url, exc)

    def load_config(self) -> WebhooksConfig:
        """Return resolved webhook config for this namespace's active _webhooks version."""
        cached = config_cache.get(self.namespace.id)
        if cached is not None:
            return cached.config

        from ..resolving import ResolvePipelineManager

        resolved = ResolvePipelineManager.resolve_webhooks_config(self.namespace)
        if resolved is None:
            return WebhooksConfig()

        resolved_body, secret_paths = resolved
        entries_raw = resolved_body.get("webhooks", []) if isinstance(resolved_body, dict) else []
        entries: list[WebhookEntrySchema] = []
        for raw_entry in entries_raw or []:
            if not isinstance(raw_entry, dict):
                continue
            try:
                entry = WebhookEntrySchema.model_validate(raw_entry)
                entries.append(entry)
            except Exception as exc:
                logger.warning("Skipping malformed webhook entry: %s", exc)

        result = WebhooksConfig(entries=entries)
        config_cache.put(
            self.namespace.id,
            _CachedWebhooksEntry(config=result, secret_paths=secret_paths),
        )
        return result

    @staticmethod
    def _sign_body(body: bytes, key: bytes) -> str:
        return hmac.new(key, body, hashlib.sha256).hexdigest()

    @staticmethod
    def _matches_path_filter(path: str | None, patterns: list[str]) -> bool:
        if not patterns:
            return True
        if path is None:
            return False
        return any(fnmatch.fnmatch(path, pat) for pat in patterns)

    @staticmethod
    def _build_actor(auth) -> dict[str, Any]:
        if auth is None:
            return {"type": "system", "name": "Ocmo"}
        if auth.is_user:
            return {"type": "user", "email": auth.email, "name": auth.display_name}
        return {"type": "resolver", "name": auth.display_name}

    def build_event(
        self,
        event: str,
        *,
        path: str | None,
        version: int | None = None,
        tag: str | None = None,
        auth=None,
        details: dict[str, Any] | None = None,
    ) -> WebhookEvent:
        actor_auth = self.auth if auth is None else auth
        return WebhookEvent(
            event=event,
            namespace=self.namespace.name,
            path=path,
            version=version,
            tag=tag,
            actor=self._build_actor(actor_auth),
            details=details,
        )

    @staticmethod
    def _base_payload(event: WebhookEvent) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event": event.event,
            "namespace": event.namespace,
            "path": event.path,
            "version": event.version,
            "tag": event.tag,
            "actor": event.actor,
            "timestamp": event.timestamp,
        }
        if event.details is not None:
            payload["details"] = event.details
        return payload

    def build_ocmo(self, event: WebhookEvent) -> tuple[bytes, dict]:
        body = json.dumps(self._base_payload(event), separators=(",", ":")).encode()
        return body, {"Content-Type": "application/json"}

    def build_generic_json(self, event: WebhookEvent) -> tuple[bytes, dict]:
        flat: dict[str, Any] = {
            "event": event.event,
            "namespace": event.namespace,
            "path": event.path,
            "version": event.version,
            "tag": event.tag,
            "actor_type": event.actor.get("type"),
            "actor_name": event.actor.get("name") or event.actor.get("email"),
            "timestamp": event.timestamp,
        }
        if event.details is not None:
            flat["details"] = event.details
        body = json.dumps(flat, separators=(",", ":")).encode()
        return body, {"Content-Type": "application/json"}

    def build_slack(self, event: WebhookEvent) -> tuple[bytes, dict]:
        text = f"*{event.event}* on `{event.namespace}/{event.path}`"
        actor_label = event.actor.get("email") or event.actor.get("name") or "system"
        fields = [
            {"title": "Namespace", "value": event.namespace, "short": True},
            {"title": "Path", "value": event.path or "(none)", "short": True},
            {"title": "Event", "value": event.event, "short": True},
            {"title": "Actor", "value": actor_label, "short": True},
            {"title": "Timestamp", "value": event.timestamp, "short": False},
        ]
        if event.version is not None:
            fields.append({"title": "Version", "value": str(event.version), "short": True})
        if event.tag is not None:
            fields.append({"title": "Tag", "value": event.tag, "short": True})
        payload = {"attachments": [{"text": text, "fields": fields, "color": "#36a64f"}]}
        body = json.dumps(payload, separators=(",", ":")).encode()
        return body, {"Content-Type": "application/json"}

    def build_teams(self, event: WebhookEvent) -> tuple[bytes, dict]:
        actor_label = event.actor.get("email") or event.actor.get("name") or "system"
        facts = [
            {"title": "Event", "value": event.event},
            {"title": "Namespace", "value": event.namespace},
            {"title": "Path", "value": event.path or "(none)"},
            {"title": "Actor", "value": actor_label},
            {"title": "Timestamp", "value": event.timestamp},
        ]
        if event.version is not None:
            facts.append({"title": "Version", "value": str(event.version)})
        if event.tag is not None:
            facts.append({"title": "Tag", "value": event.tag})
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": f"{event.event} on {event.namespace}/{event.path}",
            "sections": [{"facts": facts}],
        }
        body = json.dumps(payload, separators=(",", ":")).encode()
        return body, {"Content-Type": "application/json"}

    def build_discord(self, event: WebhookEvent) -> tuple[bytes, dict]:
        actor_label = event.actor.get("email") or event.actor.get("name") or "system"
        fields = [
            {"name": "Path", "value": event.path or "(none)", "inline": True},
            {"name": "Actor", "value": actor_label, "inline": True},
        ]
        if event.version is not None:
            fields.append({"name": "Version", "value": str(event.version), "inline": True})
        payload = {
            "embeds": [
                {
                    "title": event.event,
                    "description": f"**{event.namespace}** — {event.timestamp}",
                    "fields": fields,
                }
            ]
        }
        body = json.dumps(payload, separators=(",", ":")).encode()
        return body, {"Content-Type": "application/json"}

    def build_payload(
        self,
        event: WebhookEvent,
        *,
        preset: str | None = None,
        template: str | None = None,
        extra_headers: dict | None = None,
    ) -> tuple[bytes, dict]:
        if preset and template:
            logger.warning("Webhook entry has both preset and template set; using ocmo preset")
            preset, template = "ocmo", None

        headers: dict = {}
        if extra_headers:
            headers.update(extra_headers)

        if template:
            env = make_template_environment()
            ctx: dict[str, Any] = {
                "event": event.event,
                "namespace": event.namespace,
                "path": event.path,
                "version": event.version,
                "tag": event.tag,
                "actor": event.actor,
                "timestamp": event.timestamp,
            }
            if event.details is not None:
                ctx["details"] = event.details
            try:
                rendered = env.from_string(template).render(**ctx)
            except Exception as exc:
                logger.warning("Webhook template render failed: %s; falling back to ocmo preset", exc)
                body, ct_headers = self.build_ocmo(event)
                headers.update(ct_headers)
                return body, headers
            body = rendered.encode()
            return body, headers

        presets = {
            "ocmo": self.build_ocmo,
            "generic_json": self.build_generic_json,
            "slack": self.build_slack,
            "teams": self.build_teams,
            "discord": self.build_discord,
        }
        builder = presets.get(preset or "ocmo", self.build_ocmo)
        body, ct_headers = builder(event)
        headers.update(ct_headers)
        return body, headers

    def dispatch(self, event: WebhookEvent) -> None:
        """Fan out *event* to all matching enabled webhook entries for this namespace."""
        try:
            config = self.load_config()
        except Exception as exc:
            logger.warning("Failed to load webhooks config for %s: %s", self.namespace.name, exc)
            return

        if not config.entries:
            return

        deliveries: list[tuple[str, str, bytes, dict]] = []

        for entry in config.entries:
            if not entry.enabled:
                continue
            if event.event not in entry.events:
                continue
            path_patterns = entry.filter.paths if entry.filter else []
            if not self._matches_path_filter(event.path, path_patterns):
                continue

            payload_cfg = entry.payload
            body, headers = self.build_payload(
                event,
                preset=payload_cfg.preset,
                template=payload_cfg.template,
                extra_headers=dict(payload_cfg.headers) if payload_cfg.headers else None,
            )

            raw_key = entry.signature_key.encode("utf-8")
            if not raw_key:
                logger.warning(
                    "Webhook %r has empty signing key; skipping unsigned delivery",
                    entry.id,
                )
                continue

            sig = self._sign_body(body, raw_key)
            headers[entry.signature_header] = sig
            deliveries.append((entry.id, entry.url, body, dict(headers)))

        if not deliveries:
            return

        def _send_all(items=deliveries):
            for wid, url, body, hdrs in items:
                t = threading.Thread(
                    target=WebhookManager.deliver,
                    args=(wid, url, body, hdrs),
                    daemon=True,
                )
                t.start()

        try:
            transaction.on_commit(_send_all)
        except Exception:
            _send_all()
