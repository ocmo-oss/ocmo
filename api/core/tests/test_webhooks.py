"""Webhook delivery tests.

Covers:
- WebhookManager.load_config: tag pointer, empty list, cache
- WebhookManager.dispatch: event/path filtering, HMAC, preset shapes,
  Jinja2 template, custom headers
- Integration hooks: config create/update/delete/tag, secret CRUD/tag,
  namespace.updated, config.resolved, secret.resolved, lock.created/deleted,
  propagation.triggered
- Built-in paths deliverable when subscribed
- Delivery failure isolation (API still returns 2xx)
- on_commit scheduling
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase, override_settings

from core.managers.namespace import NamespaceManager
from core.managers.resolving import ResolvePipelineManager
from core.managers.secret import SecretManager
from core.managers.tree import TreeManager
from core.managers.webhook import (
    WebhookEvent,
    WebhookManager,
)
from core.models import Namespace

_TEST_MASTER_KEY = "ZDPuvW6Hx/1UxDK7K/CydLouVKtJl24nbHyb2EkvTzs="

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

# Minimal _webhooks YAML with HMAC signing key hard-coded as a plain string
# (not via secret reference) to avoid needing encrypted secrets in most tests.
_WEBHOOKS_CFG = """\
webhooks:
  - id: test-hook
    enabled: true
    url: https://hooks.example.com/ocmo
    events:
      - config.created
      - config.updated
      - config.deleted
      - config.tagged
      - config.resolved
      - secret.resolved
      - secret.created
      - secret.updated
      - secret.deleted
      - secret.tagged
      - resolver.created
      - resolver.updated
      - namespace.updated
      - lock.created
      - lock.updated
      - lock.deleted
      - propagation.triggered
    signature_header: X-Hook-Sig
    signature_key: "test-hmac-key-1234"
    payload:
      preset: ocmo
"""

_WEBHOOKS_SLACK = """\
webhooks:
  - id: slack-hook
    enabled: true
    url: https://hooks.slack.com/services/T/B/X
    events:
      - config.updated
    signature_key: "test-hmac-key-1234"
    payload:
      preset: slack
"""

_WEBHOOKS_TEMPLATE = """\
webhooks:
  - id: tmpl-hook
    enabled: true
    url: https://example.com/hook
    events:
      - config.updated
    signature_key: "test-hmac-key-1234"
    payload:
      template: '{"evt":"{{ event }}","ns":"{{ namespace }}"}'
      headers:
        X-Custom: my-token
"""

_WEBHOOKS_PATH_FILTER = """\
webhooks:
  - id: filtered-hook
    enabled: true
    url: https://hooks.example.com/filtered
    events:
      - config.updated
    filter:
      paths:
        - project/prod/**
    signature_key: "test-hmac-key-1234"
    payload:
      preset: ocmo
"""

_WEBHOOKS_PARAM = """\
_ocmo:
  parameters:
    hmac_key:
      type: secret
      value: _webhooks_secret@latest
      description: HMAC signing key for webhook payloads
webhooks:
  - id: param-hook
    enabled: true
    url: https://hooks.example.com/param
    events:
      - config.updated
    signature_header: X-Hook-Sig
    signature_key: "{!hmac_key}"
    payload:
      preset: ocmo
"""

_WEBHOOKS_DUAL_KEY = """\
_ocmo:
  parameters:
    key_a:
      type: secret
      value: _webhooks_secret@latest
      description: First webhook signing key
    key_b:
      type: secret
      value: creds/partner@latest
      description: Second webhook signing key
webhooks:
  - id: hook-a
    enabled: true
    url: https://hooks.example.com/a
    events:
      - config.updated
    signature_key: "{!key_a}"
    payload:
      preset: ocmo
  - id: hook-b
    enabled: true
    url: https://hooks.example.com/b
    events:
      - config.updated
    signature_key: "{!key_b}"
    payload:
      preset: ocmo
"""

_PROPAGATION_RULES = """\
_ocmo:
  propagation:
    enabled: true
    trigger: manual
    targets:
      - proj/target@latest
mode: data
key: source
"""


def _set_webhooks_secret(ns: Namespace, value: str) -> None:
    SecretManager(ns, "_webhooks_secret", auth=None).update(value)


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class WebhooksConfigLoaderTests(TestCase):
    """Unit tests for WebhookManager.load_config."""

    def setUp(self):
        WebhookManager._config_cache.clear()
        self.ns = _create_full_test_namespace("wh-loader-test")

    def tearDown(self):
        WebhookManager._config_cache.clear()

    def test_bootstrap_has_disabled_example_entry(self):
        cfg = WebhookManager(self.ns).load_config()
        self.assertEqual(len(cfg.entries), 1)
        self.assertEqual(cfg.entries[0].id, "example")
        self.assertFalse(cfg.entries[0].enabled)
        self.assertNotEqual(cfg.entries[0].signature_key, "{!hmac_signing_key}")

    def test_populated_webhooks_parsed(self):
        TreeManager(self.ns, "_webhooks", auth=None).update_item(_WEBHOOKS_CFG)
        self.ns.refresh_from_db()
        cfg = WebhookManager(self.ns).load_config()
        self.assertEqual(len(cfg.entries), 1)
        self.assertEqual(cfg.entries[0].id, "test-hook")

    def test_load_config_does_not_fire_secret_resolved(self):
        _set_webhooks_secret(self.ns, "signing-key")
        TreeManager(self.ns, "_webhooks", auth=None).update_item(_WEBHOOKS_PARAM)
        self.ns.refresh_from_db()
        WebhookManager.invalidate(self.ns.id)
        with patch("requests.post") as mock_post:
            WebhookManager(self.ns, auth=None).load_config()
            mock_post.assert_not_called()

    def test_load_config_uses_resolve_for_param_signature_key(self):
        _set_webhooks_secret(self.ns, "resolved-secret-key")
        TreeManager(self.ns, "_webhooks", auth=None).update_item(_WEBHOOKS_PARAM)
        self.ns.refresh_from_db()
        WebhookManager.invalidate(self.ns.id)
        cfg = WebhookManager(self.ns).load_config()
        self.assertEqual(cfg.entries[0].signature_key, "resolved-secret-key")

    def test_cache_hit_avoids_second_resolve(self):
        TreeManager(self.ns, "_webhooks", auth=None).update_item(_WEBHOOKS_CFG)
        self.ns.refresh_from_db()
        WebhookManager.invalidate(self.ns.id)
        resolve_calls: list[int] = []
        original = ResolvePipelineManager.resolve_data_only

        def counting_resolve(self, chain):
            resolve_calls.append(1)
            return original(self, chain)

        with patch.object(ResolvePipelineManager, "resolve_data_only", counting_resolve):
            mgr = WebhookManager(self.ns)
            mgr.load_config()
            mgr.load_config()
        self.assertEqual(len(resolve_calls), 1)

    def test_cache_invalidated_on_webhooks_update(self):
        TreeManager(self.ns, "_webhooks", auth=None).update_item(_WEBHOOKS_CFG)
        self.ns.refresh_from_db()
        WebhookManager.invalidate(self.ns.id)
        resolve_calls: list[int] = []
        original = ResolvePipelineManager.resolve_data_only

        def counting_resolve(self, chain):
            resolve_calls.append(1)
            return original(self, chain)

        with patch.object(ResolvePipelineManager, "resolve_data_only", counting_resolve):
            WebhookManager(self.ns).load_config()
            WebhookManager.invalidate(self.ns.id)
            WebhookManager(self.ns).load_config()
        self.assertEqual(len(resolve_calls), 2)

    def test_missing_webhooks_config_returns_empty(self):
        # Namespace without _webhooks config should not crash
        ns2 = Namespace.objects.create(name="wh-no-config", description="test")
        cfg = WebhookManager(ns2).load_config()
        self.assertEqual(cfg.entries, [])


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class PayloadBuilderTests(TestCase):
    """Unit tests for payload preset and template builders."""

    def setUp(self):
        self.mgr = WebhookManager(Namespace(name="ns1"))

    def _event(self, **kwargs) -> WebhookEvent:
        defaults = {
            "event": "config.updated",
            "namespace": "ns1",
            "path": "project/prod/app",
            "version": 3,
            "tag": None,
            "actor": {"type": "user", "email": "alice@example.com"},
        }
        defaults.update(kwargs)
        return WebhookEvent(**defaults)

    def test_ocmo_preset_shape(self):
        evt = self._event()
        body, headers = self.mgr.build_ocmo(evt)
        data = json.loads(body)
        self.assertEqual(data["event"], "config.updated")
        self.assertEqual(data["namespace"], "ns1")
        self.assertEqual(data["path"], "project/prod/app")
        self.assertEqual(data["version"], 3)
        self.assertIn("actor", data)
        self.assertIn("timestamp", data)
        self.assertNotIn("details", data)  # omitted when None

    def test_ocmo_preset_includes_details_when_set(self):
        evt = self._event(details={"reason": "freeze", "locked_by": "alice@example.com"})
        body, _ = self.mgr.build_ocmo(evt)
        data = json.loads(body)
        self.assertIn("details", data)
        self.assertEqual(data["details"]["reason"], "freeze")

    def test_generic_json_preset_flat(self):
        evt = self._event()
        body, _ = self.mgr.build_generic_json(evt)
        data = json.loads(body)
        self.assertIn("actor_type", data)
        self.assertNotIn("actor", data)  # actor is split into flat fields

    def test_slack_preset_has_attachments(self):
        evt = self._event()
        body, _ = self.mgr.build_slack(evt)
        data = json.loads(body)
        self.assertIn("attachments", data)
        self.assertTrue(len(data["attachments"]) > 0)

    def test_jinja2_template_rendered(self):
        evt = self._event()
        body, headers = self.mgr.build_payload(evt, template='{"e":"{{ event }}"}')
        self.assertIn(b'"config.updated"', body)

    def test_jinja2_template_custom_headers_merged(self):
        evt = self._event()
        _, headers = self.mgr.build_payload(
            evt,
            template='{"e":"{{ event }}"}',
            extra_headers={"X-Custom": "my-token"},
        )
        self.assertEqual(headers.get("X-Custom"), "my-token")

    def test_both_preset_and_template_falls_back_to_ocmo(self):
        evt = self._event()
        body, headers = self.mgr.build_payload(evt, preset="ocmo", template='{"x":"y"}')
        data = json.loads(body)
        self.assertIn("event", data)  # ocmo shape

    def test_unknown_preset_falls_back_to_ocmo(self):
        evt = self._event()
        body, _ = self.mgr.build_payload(evt, preset="nonexistent")
        data = json.loads(body)
        self.assertIn("event", data)


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class WebhookDispatchUnitTests(TestCase):
    """Unit tests for WebhookManager.dispatch filtering, HMAC, and delivery."""

    def setUp(self):
        WebhookManager._config_cache.clear()
        self.ns = _create_full_test_namespace("wh-dispatch-test")

    def tearDown(self):
        WebhookManager._config_cache.clear()

    def _set_webhooks(self, yaml_doc: str):
        TreeManager(self.ns, "_webhooks", auth=None).update_item(yaml_doc)
        self.ns.refresh_from_db()
        WebhookManager._config_cache.clear()

    def _mgr(self) -> WebhookManager:
        return WebhookManager(self.ns)

    def _event(self, event="config.updated", path="app/cfg", version=1) -> WebhookEvent:
        return self._mgr().build_event(event, path=path, version=version)

    def test_empty_webhooks_no_http(self):
        with patch("requests.post") as mock_post:
            self._mgr().dispatch(self._event())
            mock_post.assert_not_called()

    def test_event_mismatch_no_delivery(self):
        self._set_webhooks(_WEBHOOKS_CFG)
        evt = self._mgr().build_event("config.created_UNKNOWN", path="app/cfg")
        with patch("requests.post") as mock_post:
            with self.captureOnCommitCallbacks(execute=True):
                self._mgr().dispatch(evt)
            mock_post.assert_not_called()

    def test_event_match_delivers(self):
        self._set_webhooks(_WEBHOOKS_CFG)
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                self._mgr().dispatch(self._event("config.updated"))
            mock_post.assert_called_once()
            url = mock_post.call_args[0][0]
            self.assertEqual(url, "https://hooks.example.com/ocmo")

    def test_hmac_signature_header_correct(self):
        self._set_webhooks(_WEBHOOKS_CFG)
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                self._mgr().dispatch(self._event("config.updated"))
            _, kwargs = mock_post.call_args
            headers = (
                kwargs.get("headers")
                or mock_post.call_args[1].get("headers")
                or mock_post.call_args.kwargs.get("headers")
            )
            body = kwargs.get("data") or mock_post.call_args.kwargs.get("data")
            key = b"test-hmac-key-1234"
            expected_sig = hmac.new(key, body, hashlib.sha256).hexdigest()
            self.assertEqual(headers["X-Hook-Sig"], expected_sig)

    def test_custom_signature_header_name(self):
        self._set_webhooks(_WEBHOOKS_CFG)
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                self._mgr().dispatch(self._event("config.updated"))
            headers = mock_post.call_args.kwargs.get("headers") or mock_post.call_args[1]["headers"]
            self.assertIn("X-Hook-Sig", headers)

    def test_path_filter_match(self):
        self._set_webhooks(_WEBHOOKS_PATH_FILTER)
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                self._mgr().dispatch(
                    self._mgr().build_event("config.updated", path="project/prod/api"),
                )
            mock_post.assert_called_once()

    def test_path_filter_no_match(self):
        self._set_webhooks(_WEBHOOKS_PATH_FILTER)
        with patch("requests.post") as mock_post:
            with self.captureOnCommitCallbacks(execute=True):
                self._mgr().dispatch(
                    self._mgr().build_event("config.updated", path="project/dev/api"),
                )
            mock_post.assert_not_called()

    def test_disabled_entry_skipped(self):
        disabled_cfg = _WEBHOOKS_CFG.replace("enabled: true", "enabled: false")
        self._set_webhooks(disabled_cfg)
        with patch("requests.post") as mock_post:
            with self.captureOnCommitCallbacks(execute=True):
                self._mgr().dispatch(self._event("config.updated"))
            mock_post.assert_not_called()

    def test_slack_preset_delivered(self):
        self._set_webhooks(_WEBHOOKS_SLACK)
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                self._mgr().dispatch(self._event("config.updated"))
            mock_post.assert_called_once()
            body = mock_post.call_args.kwargs.get("data") or mock_post.call_args[1]["data"]
            data = json.loads(body)
            self.assertIn("attachments", data)

    def test_template_delivered_with_custom_header(self):
        self._set_webhooks(_WEBHOOKS_TEMPLATE)
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                self._mgr().dispatch(self._event("config.updated"))
            mock_post.assert_called_once()
            headers = mock_post.call_args.kwargs.get("headers") or mock_post.call_args[1]["headers"]
            self.assertEqual(headers.get("X-Custom"), "my-token")
            body = mock_post.call_args.kwargs.get("data") or mock_post.call_args[1]["data"]
            data = json.loads(body)
            self.assertEqual(data["evt"], "config.updated")

    def test_per_entry_different_signing_keys(self):
        _set_webhooks_secret(self.ns, "key-alpha")
        SecretManager(self.ns, "creds/partner", auth=None).create("key-beta")
        self._set_webhooks(_WEBHOOKS_DUAL_KEY)
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                self._mgr().dispatch(self._event("config.updated"))
            self.assertEqual(mock_post.call_count, 2)
            calls = mock_post.call_args_list
            body_a = calls[0].kwargs.get("data") or calls[0][1]["data"]
            body_b = calls[1].kwargs.get("data") or calls[1][1]["data"]
            sig_a = (calls[0].kwargs.get("headers") or calls[0][1]["headers"])["X-OCMO-Signature"]
            sig_b = (calls[1].kwargs.get("headers") or calls[1][1]["headers"])["X-OCMO-Signature"]
            self.assertEqual(
                sig_a,
                hmac.new(b"key-alpha", body_a, hashlib.sha256).hexdigest(),
            )
            self.assertEqual(
                sig_b,
                hmac.new(b"key-beta", body_b, hashlib.sha256).hexdigest(),
            )

    def test_secret_update_invalidates_cached_signing_key(self):
        _set_webhooks_secret(self.ns, "old-key")
        self._set_webhooks(_WEBHOOKS_PARAM)
        self._mgr().load_config()
        _set_webhooks_secret(self.ns, "new-key")
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                self._mgr().dispatch(self._event("config.updated"))
            body = mock_post.call_args.kwargs.get("data") or mock_post.call_args[1]["data"]
            sig = (mock_post.call_args.kwargs.get("headers") or mock_post.call_args[1]["headers"])["X-Hook-Sig"]
            self.assertEqual(sig, hmac.new(b"new-key", body, hashlib.sha256).hexdigest())

    def test_unrelated_secret_update_keeps_webhook_cache(self):
        _set_webhooks_secret(self.ns, "cached-key")
        self._set_webhooks(_WEBHOOKS_PARAM)
        resolve_calls: list[int] = []
        original = ResolvePipelineManager.resolve_data_only

        def counting_resolve(self, chain):
            resolve_calls.append(1)
            return original(self, chain)

        with patch.object(ResolvePipelineManager, "resolve_data_only", counting_resolve):
            self._mgr().load_config()
            SecretManager(self.ns, "creds/unrelated", auth=None).create("other-secret")
            self._mgr().load_config()
        self.assertEqual(len(resolve_calls), 1)

    def test_delivery_failure_does_not_propagate(self):
        self._set_webhooks(_WEBHOOKS_CFG)
        with patch("requests.post", side_effect=Exception("timeout")):
            with self.captureOnCommitCallbacks(execute=True):
                self._mgr().dispatch(self._event("config.updated"))


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class WebhookSchemaValidationTests(TestCase):
    def setUp(self):
        WebhookManager._config_cache.clear()
        self.ns = _create_full_test_namespace("wh-schema-test")

    def test_signature_key_required_on_save(self):
        from django.core.exceptions import ValidationError

        bad_cfg = """\
webhooks:
  - id: bad-hook
    enabled: true
    url: https://example.com/hook
    events:
      - config.updated
    payload:
      preset: ocmo
"""
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "_webhooks", auth=None).update_item(bad_cfg)


def _create_full_test_namespace(name: str) -> Namespace:
    """Create a namespace with ALL built-in configs + open permissions."""
    from core.managers.namespace import NamespaceManager as _NM
    from core.utils.namespace_special_configs import init_namespace_special_configs

    ns = Namespace.objects.create(name=name, description="test")
    mgr = _NM(name, auth=None)
    mgr.ns = ns
    init_namespace_special_configs(ns)
    # Set permissive policies so API client calls work without auth
    TreeManager(ns, "_permissions", auth=None).update_item(_OPEN_PERMISSIONS)
    return ns


@override_settings(OCMO_MASTER_KEY=_TEST_MASTER_KEY)
class WebhookIntegrationTests(TestCase):
    """End-to-end integration tests verifying hook wiring in manager methods."""

    def setUp(self):
        WebhookManager._config_cache.clear()
        self.client = Client()
        self.ns = _create_full_test_namespace("wh-int-test")
        # Configure webhooks
        TreeManager(self.ns, "_webhooks", auth=None).update_item(_WEBHOOKS_CFG)
        self.ns.refresh_from_db()
        WebhookManager._config_cache.clear()

    def tearDown(self):
        WebhookManager._config_cache.clear()

    # --- config CRUD via API ---

    def test_config_create_fires_event(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.post(
                    f"/api/v1/ns/{self.ns.name}/~config/~create/app/cfg",
                    data=b"key: val\n",
                    content_type="application/yaml",
                )
            self.assertEqual(resp.status_code, 201, resp.content)
            # At least one call should be for config.created
            events = [json.loads(c.kwargs.get("data") or c[1]["data"])["event"] for c in mock_post.call_args_list]
            self.assertIn("config.created", events)

    def test_config_update_fires_event(self):
        self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/app/upd",
            data=b"key: val\n",
            content_type="application/yaml",
        )
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.put(
                    f"/api/v1/ns/{self.ns.name}/~config/~update/app/upd",
                    data=b"key: changed\n",
                    content_type="application/yaml",
                )
            self.assertEqual(resp.status_code, 200, resp.content)
            events = [json.loads(c.kwargs.get("data") or c[1]["data"])["event"] for c in mock_post.call_args_list]
            self.assertIn("config.updated", events)

    def test_config_delete_fires_event(self):
        self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/app/del",
            data=b"key: val\n",
            content_type="application/yaml",
        )
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.delete(
                    f"/api/v1/ns/{self.ns.name}/~delete/app/del?preview=false",
                )
            self.assertEqual(resp.status_code, 200, resp.content)
            events = [json.loads(c.kwargs.get("data") or c[1]["data"])["event"] for c in mock_post.call_args_list]
            self.assertIn("config.deleted", events)

    def test_config_tag_fires_event(self):
        self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/app/tagged",
            data=b"key: val\n",
            content_type="application/yaml",
        )
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.post(
                    f"/api/v1/ns/{self.ns.name}/~tag/app/tagged",
                    data=json.dumps({"tag": "mytag", "version": 1}),
                    content_type="application/json",
                )
            self.assertEqual(resp.status_code, 200, resp.content)
            events = [json.loads(c.kwargs.get("data") or c[1]["data"])["event"] for c in mock_post.call_args_list]
            self.assertIn("config.tagged", events)

    # --- namespace.updated ---

    def test_namespace_updated_fires_event(self):
        from core.schemas.requests import NamespacePatchSchema

        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                NamespaceManager(self.ns.name, auth=None).update(NamespacePatchSchema(description="updated directly"))
            events = [json.loads(c.kwargs.get("data") or c[1]["data"])["event"] for c in mock_post.call_args_list]
            self.assertIn("namespace.updated", events)
            namespace_events = [
                json.loads(c.kwargs.get("data") or c[1]["data"])
                for c in mock_post.call_args_list
                if json.loads(c.kwargs.get("data") or c[1]["data"])["event"] == "namespace.updated"
            ]
            self.assertIsNone(namespace_events[0]["path"])

    # --- lock events ---

    def test_lock_created_fires_event(self):
        self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/lockable/cfg",
            data=b"key: val\n",
            content_type="application/yaml",
        )
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.post(
                    f"/api/v1/ns/{self.ns.name}/~lock/lockable/cfg",
                    data=json.dumps({"reason": "freeze"}),
                    content_type="application/json",
                )
            self.assertEqual(resp.status_code, 201, resp.content)
            events = [json.loads(c.kwargs.get("data") or c[1]["data"])["event"] for c in mock_post.call_args_list]
            self.assertIn("lock.created", events)
            lock_evt = next(
                json.loads(c.kwargs.get("data") or c[1]["data"])
                for c in mock_post.call_args_list
                if json.loads(c.kwargs.get("data") or c[1]["data"])["event"] == "lock.created"
            )
            self.assertEqual(lock_evt["details"]["reason"], "freeze")

    def test_lock_deleted_fires_event(self):
        self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/lockable/del",
            data=b"key: val\n",
            content_type="application/yaml",
        )
        self.client.post(
            f"/api/v1/ns/{self.ns.name}/~lock/lockable/del",
            data=json.dumps({"reason": "freeze"}),
            content_type="application/json",
        )
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.delete(f"/api/v1/ns/{self.ns.name}/~lock/lockable/del")
            self.assertEqual(resp.status_code, 204, resp.content)
            events = [json.loads(c.kwargs.get("data") or c[1]["data"])["event"] for c in mock_post.call_args_list]
            self.assertIn("lock.deleted", events)

    # --- secret events ---

    def test_secret_created_fires_event(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.post(
                    f"/api/v1/ns/{self.ns.name}/~secret/~create/creds/db",
                    data=b"password: secret123\n",
                    content_type="application/yaml",
                )
            self.assertEqual(resp.status_code, 201, resp.content)
            events = [json.loads(c.kwargs.get("data") or c[1]["data"])["event"] for c in mock_post.call_args_list]
            self.assertIn("secret.created", events)

    def test_secret_payload_has_no_plaintext(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(
                    f"/api/v1/ns/{self.ns.name}/~secret/~create/creds/safe",
                    data=b"password: super-secret\n",
                    content_type="application/yaml",
                )
            for c in mock_post.call_args_list:
                body_str = (c.kwargs.get("data") or c[1]["data"]).decode()
                self.assertNotIn("super-secret", body_str)

    def test_secret_updated_fires_event(self):
        SecretManager(self.ns, "creds/upd", auth=None).create("password: first\n")
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.put(
                    f"/api/v1/ns/{self.ns.name}/~secret/~update/creds/upd",
                    data=b"password: second\n",
                    content_type="application/yaml",
                )
            self.assertEqual(resp.status_code, 200, resp.content)
            events = [json.loads(c.kwargs.get("data") or c[1]["data"])["event"] for c in mock_post.call_args_list]
            self.assertIn("secret.updated", events)

    def test_secret_deleted_fires_event(self):
        SecretManager(self.ns, "creds/del", auth=None).create("password: pass\n")
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.delete(
                    f"/api/v1/ns/{self.ns.name}/~delete/creds/del?preview=false",
                )
            self.assertEqual(resp.status_code, 200, resp.content)
            events = [json.loads(c.kwargs.get("data") or c[1]["data"])["event"] for c in mock_post.call_args_list]
            self.assertIn("secret.deleted", events)

    def test_secret_tagged_fires_event(self):
        SecretManager(self.ns, "creds/tag", auth=None).create("password: pass\n")
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.post(
                    f"/api/v1/ns/{self.ns.name}/~tag/creds/tag",
                    data=json.dumps({"tag": "mytag", "version": 1}),
                    content_type="application/json",
                )
            self.assertEqual(resp.status_code, 200, resp.content)
            events = [json.loads(c.kwargs.get("data") or c[1]["data"])["event"] for c in mock_post.call_args_list]
            self.assertIn("secret.tagged", events)

    # --- built-in path deliverable when subscribed ---

    def test_builtin_path_deliverable_when_subscribed(self):
        """Updating _permissions fires config.updated when subscribed."""
        cfg_with_perm_filter = """\
webhooks:
  - id: perm-audit
    enabled: true
    url: https://hooks.example.com/perms
    events:
      - config.updated
    filter:
      paths:
        - _permissions
    signature_key: "test-hmac-key-1234"
    payload:
      preset: ocmo
"""
        TreeManager(self.ns, "_webhooks", auth=None).update_item(cfg_with_perm_filter)
        self.ns.refresh_from_db()
        WebhookManager._config_cache.clear()
        # Use different content from what's already stored to guarantee content_changed=True
        updated_perm = _OPEN_PERMISSIONS + "# updated\n"
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                TreeManager(self.ns, "_permissions", auth=None).update_item(updated_perm)
            mock_post.assert_called_once()
            body = json.loads(mock_post.call_args.kwargs.get("data") or mock_post.call_args[1]["data"])
            self.assertEqual(body["path"], "_permissions")
            self.assertEqual(body["event"], "config.updated")

    def test_builtin_path_not_delivered_without_subscription(self):
        """Updating _permissions should NOT fire if no webhook subscribes to it."""
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            with self.captureOnCommitCallbacks(execute=True):
                TreeManager(self.ns, "_permissions", auth=None).update_item(_OPEN_PERMISSIONS)
            # _WEBHOOKS_CFG has no path filter, so _permissions IS in scope — but we
            # test that a path-filtered hook that excludes _permissions stays quiet.
            # The test above (path_filter_no_match) already covers filter exclusion;
            # here we just verify the built-in path triggers normally.
            # Reset to a filtered hook that won't match _permissions.
        TreeManager(self.ns, "_webhooks", auth=None).update_item(_WEBHOOKS_PATH_FILTER)
        self.ns.refresh_from_db()
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            with self.captureOnCommitCallbacks(execute=True):
                TreeManager(self.ns, "_permissions", auth=None).update_item(_OPEN_PERMISSIONS)
            mock_post.assert_not_called()

    # --- propagation ---

    def test_propagation_triggered_fires_on_manual(self):
        # Set up source and target configs
        self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/proj/source",
            data=_PROPAGATION_RULES.encode(),
            content_type="application/yaml",
        )
        self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/proj/target",
            data=b"mode: data\nkey: target\n",
            content_type="application/yaml",
        )
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.post(
                    f"/api/v1/ns/{self.ns.name}/~propagate/proj/source",
                )
            self.assertEqual(resp.status_code, 200, resp.content)
            events = [json.loads(c.kwargs.get("data") or c[1]["data"])["event"] for c in mock_post.call_args_list]
            self.assertIn("propagation.triggered", events)
            prop_evt = next(
                json.loads(c.kwargs.get("data") or c[1]["data"])
                for c in mock_post.call_args_list
                if json.loads(c.kwargs.get("data") or c[1]["data"])["event"] == "propagation.triggered"
            )
            self.assertEqual(prop_evt["path"], "proj/source")
            self.assertIn("targets", prop_evt["details"])

    # --- delivery failure isolation ---

    def test_delivery_failure_does_not_fail_api(self):
        with patch("requests.post", side_effect=Exception("network error")):
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.post(
                    f"/api/v1/ns/{self.ns.name}/~config/~create/app/isolated",
                    data=b"key: val\n",
                    content_type="application/yaml",
                )
            self.assertEqual(resp.status_code, 201)

    # --- config.resolved / secret.resolved ---

    def test_config_resolved_fires_on_resolve(self):
        self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/app/resolvable",
            data=b"key: val\n",
            content_type="application/yaml",
        )
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.get(
                    f"/api/v1/ns/{self.ns.name}/~resolve/app/resolvable",
                )
            self.assertEqual(resp.status_code, 200, resp.content)
            events = [json.loads(c.kwargs.get("data") or c[1]["data"])["event"] for c in mock_post.call_args_list]
            self.assertIn("config.resolved", events)

    def test_secret_resolved_fires_on_config_resolve(self):
        SecretManager(self.ns, "creds/db", auth=None).create("password: db-secret\n")
        self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/app/with-secret",
            data=(
                b"_ocmo:\n"
                b"  parameters:\n"
                b"    db_pass:\n"
                b"      type: secret\n"
                b"      value: creds/db@latest\n"
                b"      description: Database password\n"
                b'key: "{!db_pass}"\n'
            ),
            content_type="application/yaml",
        )
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.get(
                    f"/api/v1/ns/{self.ns.name}/~resolve/app/with-secret",
                )
            self.assertEqual(resp.status_code, 200, resp.content)
            payloads = [json.loads(c.kwargs.get("data") or c[1]["data"]) for c in mock_post.call_args_list]
            events = [p["event"] for p in payloads]
            self.assertIn("secret.resolved", events)
            secret_evt = next(p for p in payloads if p["event"] == "secret.resolved")
            self.assertEqual(secret_evt["path"], "creds/db")
            self.assertEqual(secret_evt["details"]["config_path"], "app/with-secret")
            self.assertEqual(secret_evt["details"]["ref"], "latest")

    def test_secret_resolved_payload_has_no_plaintext(self):
        SecretManager(self.ns, "creds/safe", auth=None).create("token: ultra-secret\n")
        self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/app/safe-secret",
            data=(
                b"_ocmo:\n"
                b"  parameters:\n"
                b"    tok:\n"
                b"      type: secret\n"
                b"      value: creds/safe@latest\n"
                b"      description: API token\n"
                b'key: "{!tok}"\n'
            ),
            content_type="application/yaml",
        )
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                self.client.get(
                    f"/api/v1/ns/{self.ns.name}/~resolve/app/safe-secret",
                )
            for c in mock_post.call_args_list:
                body_str = (c.kwargs.get("data") or c[1]["data"]).decode()
                self.assertNotIn("ultra-secret", body_str)

    def test_secret_resolved_skipped_with_no_creds(self):
        SecretManager(self.ns, "creds/nc", auth=None).create("token: hidden\n")
        self.client.post(
            f"/api/v1/ns/{self.ns.name}/~config/~create/app/nc-secret",
            data=(
                b"_ocmo:\n"
                b"  parameters:\n"
                b"    tok:\n"
                b"      type: secret\n"
                b"      value: creds/nc@latest\n"
                b"      description: API token\n"
                b'key: "{!tok}"\n'
            ),
            content_type="application/yaml",
        )
        WebhookManager._config_cache.clear()
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(ok=True, status_code=200)
            with self.captureOnCommitCallbacks(execute=True):
                resp = self.client.get(
                    f"/api/v1/ns/{self.ns.name}/~resolve/app/nc-secret?no-creds=true",
                )
            self.assertEqual(resp.status_code, 200, resp.content)
            events = [json.loads(c.kwargs.get("data") or c[1]["data"])["event"] for c in mock_post.call_args_list]
            self.assertIn("config.resolved", events)
            self.assertNotIn("secret.resolved", events)
