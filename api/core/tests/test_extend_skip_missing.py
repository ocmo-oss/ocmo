"""Tests for optional extend sources (skip_missing / trailing ``?``)."""

import yaml
from django.core.cache import caches
from django.core.exceptions import ValidationError
from django.test import TestCase
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import CannotResolveConfig
from core.managers.resolving import ResolvePipelineManager
from core.managers.tree import TreeManager
from core.schemas.requests import ConfigOcmoMetadataSchema, normalize_extend_ref
from core.tests.namespace_helpers import create_test_namespace


class ExtendSkipMissingSchemaTests(TestCase):
    def test_string_ref_question_suffix_sets_skip_missing(self):
        ref = normalize_extend_ref("../overlay@stable?")
        self.assertEqual(ref.path, "../overlay@stable")
        self.assertTrue(ref.skip_missing)

    def test_string_ref_question_suffix_ignores_trailing_whitespace(self):
        ref = normalize_extend_ref("../overlay@stable?  ")
        self.assertEqual(ref.path, "../overlay@stable")
        self.assertTrue(ref.skip_missing)

    def test_object_skip_missing_field(self):
        meta = ConfigOcmoMetadataSchema.model_validate(
            {
                "extend": {
                    "configs": [{"path": "shared/all@stable", "skip_missing": True}],
                },
            }
        )
        ref = normalize_extend_ref(meta.extend.configs[0])
        self.assertTrue(ref.skip_missing)

    def test_object_path_question_suffix_rejected(self):
        with self.assertRaises(PydanticValidationError):
            ConfigOcmoMetadataSchema.model_validate(
                {
                    "extend": {
                        "configs": [{"path": "shared/all@stable?"}],
                    },
                }
            )


class ExtendSkipMissingSaveValidationTests(TestCase):
    def setUp(self):
        self.ns = create_test_namespace("extend-skip-save")

    def test_save_allows_missing_optional_path(self):
        TreeManager(self.ns, "app/root", auth=None).create_item(
            """\
_ocmo:
  extend:
    configs:
      - ../optional/base?
    mode: stack
value: ok
""",
            "config",
        )

    def test_save_allows_missing_optional_version(self):
        TreeManager(self.ns, "shared/base", auth=None).create_item("tier: basic\n", "config")
        TreeManager(self.ns, "app/root", auth=None).create_item(
            """\
_ocmo:
  extend:
    configs:
      - ../shared/base@missing-tag?
    mode: stack
value: ok
""",
            "config",
        )

    def test_save_allows_optional_ref_with_unresolved_default_path(self):
        TreeManager(self.ns, "app/root", auth=None).create_item(
            """\
_ocmo:
  parameters:
    env:
      type: dynamic
      value: missing
      description: Environment name
  extend:
    configs:
      - ../bases/{!env}?
    mode: stack
value: ok
""",
            "config",
        )

    def test_save_rejects_strict_ref_with_unresolved_default_path(self):
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "app/root", auth=None).create_item(
                """\
_ocmo:
  parameters:
    env:
      type: dynamic
      value: missing
      description: Environment name
  extend:
    configs:
      - ../bases/{!env}
    mode: stack
value: ok
""",
                "config",
            )

    def test_save_rejects_wrong_type_even_when_optional(self):
        TreeManager(self.ns, "shared/tmpl", auth=None).create_item("content\n", "template")
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "app/root", auth=None).create_item(
                """\
_ocmo:
  extend:
    configs:
      - ../shared/tmpl?
    mode: stack
value: ok
""",
                "config",
            )



class ExtendSkipMissingResolveTests(TestCase):
    def setUp(self):
        self.ns = create_test_namespace("extend-skip-resolve")

    def _create(self, path: str, body: str) -> None:
        TreeManager(self.ns, path, auth=None).create_item(body, "config")

    def _resolve(self, path: str, **kwargs) -> list[dict]:
        outputs = ResolvePipelineManager(self.ns, path, "latest", auth=None, **kwargs).resolve()
        return [yaml.safe_load(o.data_text) for o in outputs]

    def _resolve_with_trace(self, path: str) -> tuple[list[dict], dict]:
        mgr = ResolvePipelineManager(self.ns, path, "latest", auth=None)
        outputs = mgr.resolve()
        data = [yaml.safe_load(o.data_text) for o in outputs]
        trace = outputs[0].trace if outputs else {}
        return data, trace

    def test_stack_skips_missing_optional(self):
        self._create("shared/required", "tier: basic\n")
        self._create(
            "app/prod",
            """\
_ocmo:
  extend:
    configs:
      - ../optional/base?
      - ../shared/required
    mode: stack
value: local
""",
        )
        self.assertEqual(self._resolve("app/prod")[0], {"tier": "basic", "value": "local"})

    def test_stack_merges_present_optional(self):
        self._create("optional/base", "overlay: enabled\n")
        self._create(
            "app/prod",
            """\
_ocmo:
  extend:
    configs:
      - ../optional/base?
    mode: stack
value: local
""",
        )
        self.assertEqual(self._resolve("app/prod")[0], {"overlay": "enabled", "value": "local"})

    def test_stack_errors_when_required_missing(self):
        with self.assertRaises(ValidationError):
            self._create(
                "app/prod",
                """\
_ocmo:
  extend:
    configs:
      - ../optional/base
    mode: stack
value: local
""",
            )

    def test_resolve_errors_when_required_missing(self):
        from core.models import ConfigVersion

        TreeManager(self.ns, "app/prod", auth=None).create_item(
            "value: local\n",
            "config",
            validate_references=False,
        )
        ConfigVersion.objects.filter(config__namespace=self.ns, config__path="app/prod", version=1).update(
            data="""\
_ocmo:
  extend:
    configs:
      - ../optional/base
    mode: stack
value: local
"""
        )
        with self.assertRaises(CannotResolveConfig):
            self._resolve("app/prod")

    def test_broadcast_skips_missing_base(self):
        self._create("bases/present", "spec:\n  image: api:1\n")
        self._create(
            "app/rollout",
            """\
_ocmo:
  extend:
    mode: broadcast
    by: .overlay
    configs:
      - ../bases/missing?
      - ../bases/present
overlay:
  replicas: 3
""",
        )
        outputs = self._resolve("app/rollout")
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0], {"spec": {"image": "api:1"}, "replicas": 3})

    def test_zip_skips_index_aligned_patch(self):
        self._create("bases/a", "defaults:\n  tier: basic\n")
        self._create(
            "app/root",
            """\
_ocmo:
  extend:
    mode: zip
    by: .patches
    configs:
      - path: ../bases/a
        key: .defaults
      - ../bases/missing?
      - path: ../bases/a
        key: .defaults
patches:
  - {tier: premium}
  - {tier: ignored}
  - {tier: standard}
""",
        )
        outputs = self._resolve("app/root")
        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[0], {"tier": "premium"})
        self.assertEqual(outputs[1], {"tier": "standard"})

    def test_replicate_returns_empty_outputs_when_optional_base_missing(self):
        self._create(
            "app/root",
            """\
_ocmo:
  extend:
    mode: replicate
    by: .data
    configs:
      - ../missing/base?
data:
  - {tier: premium}
  - {tier: standard}
label: root
""",
        )
        self.assertEqual(self._resolve("app/root"), [])

    def test_cache_miss_after_extend_ref_changes_to_optional_missing(self):
        caches["resolve"].clear()
        self._create("extend/bases/static-name", "foo: bar\n")
        self._create(
            "extend/replicate/dedup-static",
            """\
_ocmo:
  extend:
    mode: replicate
    by: .data
    configs:
      - ../bases/static-name
data:
  - {patch: a}
  - {patch: b}
  - {patch: c}
""",
        )
        warm = self._resolve("extend/replicate/dedup-static")
        self.assertEqual(len(warm), 3)
        self.assertIn("foo", warm[0])

        TreeManager(self.ns, "extend/replicate/dedup-static", auth=None).update_item(
            """\
_ocmo:
  extend:
    mode: replicate
    by: .data
    configs:
      - ../bases/static-nameXXXXXXXX?
data:
  - {patch: a}
  - {patch: b}
  - {patch: c}
"""
        )
        self.assertEqual(self._resolve("extend/replicate/dedup-static"), [])

    def test_replicate_optional_missing_base_does_not_merge_present_base(self):
        self._create("bases/static-name", "foo: bar\n")
        self._create(
            "extend/replicate/dedup-static",
            """\
_ocmo:
  extend:
    mode: replicate
    by: .data
    configs:
      - ../bases/static-nameXXXXXXXX?
data:
  - {patch: a}
  - {patch: b}
  - {patch: c}
""",
        )
        self.assertEqual(self._resolve("extend/replicate/dedup-static"), [])

    def test_replicate_normal_when_base_present(self):
        self._create("bases/base", "defaults:\n  env: prod\n")
        self._create(
            "app/root",
            """\
_ocmo:
  extend:
    mode: replicate
    by: .data
    configs:
      - ../bases/base
data:
  - {tier: premium}
  - {tier: standard}
""",
        )
        outputs = self._resolve("app/root")
        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[0], {"defaults": {"env": "prod"}, "tier": "premium"})
        self.assertEqual(outputs[1], {"defaults": {"env": "prod"}, "tier": "standard"})

    def test_param_substituted_optional_path(self):
        self._create("bases/prod", "tier: prod\n")
        self._create(
            "app/root",
            """\
_ocmo:
  parameters:
    env:
      type: dynamic
      value: prod
      description: Environment name
  extend:
    configs:
      - ../bases/{!env}?
    mode: stack
value: ok
""",
        )
        outputs = ResolvePipelineManager(
            self.ns,
            "app/root",
            "latest",
            dynamic_params={"env": "missing"},
            auth=None,
        ).resolve()
        self.assertEqual(yaml.safe_load(outputs[0].data_text), {"value": "ok"})

    def test_trace_records_skipped_ref(self):
        self._create(
            "app/root",
            """\
_ocmo:
  extend:
    configs:
      - ../optional/base?
    mode: stack
value: ok
""",
        )
        _, trace = self._resolve_with_trace("app/root")
        self.assertIn("optional/base@latest", trace)
        self.assertEqual(trace["optional/base@latest"], {"skipped": True, "reason": "not_found"})
