"""Tests for config change propagation merge behaviour."""

from django.test import TestCase

from core.managers.config_validation import ConfigValidationManager
from core.managers.propagation import PropagationManager, PropagationTargetVersion
from core.schemas.propagation import ConfigPropagationSchema


class PropagationMergeTargetTests(TestCase):
    def test_merge_overwrites_ruamel_quoted_scalar_with_plain_string(self):
        """Targets with quoted scalars (e.g. ``\"{!env}\"``) must accept propagated values."""
        target_yaml = (
            "_ocmo:\n"
            "  parameters:\n"
            "    env:\n"
            "      type: projected\n"
            "      value: .Path[1]\n"
            "      description: Environment segment from path\n"
            'environment: "{!env}"\n'
            "app:\n"
            "  name: my-service\n"
            "  replicas: 2\n"
        )
        source_payload = {
            "environment": "dev",
            "app": {"name": "my-service", "replicas": 1},
            "logging": {"level": "trace", "format": "json"},
        }
        target_metadata, _ = ConfigValidationManager.parse_config_yaml_document(target_yaml)

        merged = PropagationManager.merge_target(
            target_yaml,
            target_metadata,
            source_payload,
            "data",
        )

        self.assertIn('environment: "dev"', merged)
        self.assertNotIn('"{!env}"', merged)
        self.assertIn("replicas: 1", merged)
        self.assertIn("level: trace", merged)
        self.assertIn("type: projected", merged)

    def test_plan_propagation_marks_identical_target_unchanged(self):
        target_yaml = "key: same\n"
        source_yaml = (
            "key: same\n"
            "_ocmo:\n"
            "  propagation:\n"
            "    enabled: true\n"
            "    trigger: manual\n"
            "    targets:\n"
            "      - propagate/qa/app/config\n"
        )
        source_metadata, source_body = ConfigValidationManager.parse_config_yaml_document(source_yaml)
        target_metadata, _ = ConfigValidationManager.parse_config_yaml_document(target_yaml)
        rules = ConfigPropagationSchema.model_validate(
            {
                "enabled": True,
                "trigger": "manual",
                "mode": "data",
                "targets": ["propagate/qa/app/config"],
            }
        )

        outcomes = PropagationManager.plan_propagation(
            source_metadata=source_metadata,
            source_body=source_body,
            rules=rules,
            targets=[
                PropagationTargetVersion(
                    target_ref="propagate/qa/app/config",
                    target_path="propagate/qa/app/config",
                    version_number=1,
                    version_data=target_yaml,
                    metadata=target_metadata,
                ),
            ],
        )

        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0]["status"], "unchanged")

    def test_plan_propagation_exclude_preserves_nested_target_fields(self):
        """Exclude strips matching keys from the source before deep-merge."""
        source_yaml = (
            "_ocmo:\n"
            "  propagation:\n"
            "    enabled: true\n"
            "    trigger: manual\n"
            "    targets:\n"
            "      - propagate/perf/app/config\n"
            "    exclude:\n"
            "      - logging.level\n"
            "      - some.dev.specific.conf\n"
            "environment: dev\n"
            "logging:\n"
            "  level: trace\n"
            "  format: json\n"
            "some:\n"
            "  dev:\n"
            "    specific:\n"
            "      conf: should-not-reach-perf\n"
            "      other: from-source\n"
        )
        target_yaml = (
            "environment: perf\n"
            "logging:\n"
            "  level: warn\n"
            "  format: text\n"
            "some:\n"
            "  dev:\n"
            "    specific:\n"
            "      conf: keep-me\n"
            "      other: target-other\n"
        )
        source_metadata, source_body = ConfigValidationManager.parse_config_yaml_document(source_yaml)
        target_metadata, _ = ConfigValidationManager.parse_config_yaml_document(target_yaml)
        rules = ConfigPropagationSchema.model_validate(source_metadata.propagation.model_dump())

        outcomes = PropagationManager.plan_propagation(
            source_metadata=source_metadata,
            source_body=source_body,
            rules=rules,
            targets=[
                PropagationTargetVersion(
                    target_ref="propagate/perf/app/config",
                    target_path="propagate/perf/app/config",
                    version_number=1,
                    version_data=target_yaml,
                    metadata=target_metadata,
                ),
            ],
        )

        merged = outcomes[0]["merged_yaml"]
        self.assertEqual(outcomes[0]["status"], "updated")
        self.assertIn("conf: keep-me", merged)
        self.assertNotIn("should-not-reach-perf", merged)
        self.assertIn("level: warn", merged)
        self.assertIn("format: json", merged)
        self.assertIn("other: from-source", merged)

    def test_plan_propagation_exclude_path_must_match_nested_keys(self):
        """Exclude paths follow nested YAML keys, not underscore naming conventions."""
        source_yaml = "logging:\n  level: trace\n"
        target_yaml = "logging:\n  level: warn\n"
        source_metadata, source_body = ConfigValidationManager.parse_config_yaml_document(source_yaml)
        target_metadata, _ = ConfigValidationManager.parse_config_yaml_document(target_yaml)
        rules = ConfigPropagationSchema.model_validate(
            {
                "enabled": True,
                "trigger": "manual",
                "mode": "data",
                "targets": ["propagate/qa/app/config"],
                "exclude": ["logging.log_level"],
            }
        )

        outcomes = PropagationManager.plan_propagation(
            source_metadata=source_metadata,
            source_body=source_body,
            rules=rules,
            targets=[
                PropagationTargetVersion(
                    target_ref="propagate/qa/app/config",
                    target_path="propagate/qa/app/config",
                    version_number=1,
                    version_data=target_yaml,
                    metadata=target_metadata,
                ),
            ],
        )

        merged = outcomes[0]["merged_yaml"]
        self.assertIn("level: trace", merged)
        self.assertNotIn("level: warn", merged)

    def test_plan_propagation_exclude_does_not_match_flat_dotted_keys(self):
        """Dot paths traverse nested mappings; a single YAML key containing dots is not matched."""
        source_yaml = "some.dev.specific.conf: should-not-reach\n"
        target_yaml = "some:\n  dev:\n    specific:\n      conf: keep-me\n"
        source_metadata, source_body = ConfigValidationManager.parse_config_yaml_document(source_yaml)
        target_metadata, _ = ConfigValidationManager.parse_config_yaml_document(target_yaml)
        rules = ConfigPropagationSchema.model_validate(
            {
                "enabled": True,
                "trigger": "manual",
                "mode": "data",
                "targets": ["propagate/qa/app/config"],
                "exclude": ["some.dev.specific.conf"],
            }
        )

        outcomes = PropagationManager.plan_propagation(
            source_metadata=source_metadata,
            source_body=source_body,
            rules=rules,
            targets=[
                PropagationTargetVersion(
                    target_ref="propagate/qa/app/config",
                    target_path="propagate/qa/app/config",
                    version_number=1,
                    version_data=target_yaml,
                    metadata=target_metadata,
                ),
            ],
        )

        merged = outcomes[0]["merged_yaml"]
        self.assertIn("conf: keep-me", merged)
        self.assertIn("some.dev.specific.conf: should-not-reach", merged)


class PropagationListAndOrderTests(TestCase):
    """Regression tests for list-replace semantics and key-order preservation."""

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _run(source_yaml, target_yaml, mode="data", source_yaml_for_plan=None):
        source_metadata, source_body = ConfigValidationManager.parse_config_yaml_document(source_yaml)
        target_metadata, _ = ConfigValidationManager.parse_config_yaml_document(target_yaml)
        rules = ConfigPropagationSchema.model_validate(
            {
                "enabled": True,
                "trigger": "manual",
                "mode": mode,
                "targets": ["t/target"],
            }
        )
        outcomes = PropagationManager.plan_propagation(
            source_metadata=source_metadata,
            source_body=source_body,
            rules=rules,
            targets=[
                PropagationTargetVersion(
                    target_ref="t/target",
                    target_path="t/target",
                    version_number=1,
                    version_data=target_yaml,
                    metadata=target_metadata,
                ),
            ],
            source_yaml=source_yaml_for_plan if source_yaml_for_plan is not None else source_yaml,
        )
        return outcomes[0]

    # ------------------------------------------------------------------ list

    def test_data_mode_list_fields_replaced_not_concatenated(self):
        """Source list must replace target list, not be appended to it."""
        source_yaml = "tags:\n  - a\n  - c\n"
        target_yaml = "tags:\n  - a\n  - b\n"
        outcome = self._run(source_yaml, target_yaml)
        merged = outcome["merged_yaml"]
        self.assertEqual(outcome["status"], "updated")
        lines = [line.strip() for line in merged.splitlines() if line.strip().startswith("- ")]
        self.assertEqual(lines, ["- a", "- c"], merged)

    def test_whole_mode_transformers_not_duplicated(self):
        """mode:whole must not concatenate the transformers list from source and target."""
        source_yaml = (
            "_ocmo:\n"
            "  propagation:\n"
            "    enabled: true\n"
            "    trigger: manual\n"
            "    mode: whole\n"
            "    targets:\n"
            "      - t/target\n"
            "  parameters:\n"
            "    env:\n"
            "      type: projected\n"
            '      value: ".Path[-3]"\n'
            "      description: Environment to deploy\n"
            "      transformers:\n"
            "        - lower\n"
            "key: source\n"
        )
        target_yaml = (
            "_ocmo:\n"
            "  parameters:\n"
            "    env:\n"
            "      type: projected\n"
            '      value: ".Path[-3]"\n'
            "      description: Environment to deploy\n"
            "      transformers:\n"
            "        - lower\n"
            "key: target\n"
        )
        outcome = self._run(source_yaml, target_yaml, mode="whole")
        merged = outcome["merged_yaml"]
        self.assertEqual(outcome["status"], "updated")
        # exactly one occurrence of "lower" in the transformers list
        self.assertEqual(merged.count("- lower"), 1, merged)

    def test_whole_mode_preserves_quoted_scalar_from_source(self):
        """mode:whole must carry over quoted scalars from raw YAML (not re-serialise via Pydantic)."""
        source_yaml = (
            "_ocmo:\n"
            "  propagation:\n"
            "    enabled: true\n"
            "    trigger: manual\n"
            "    mode: whole\n"
            "    targets:\n"
            "      - t/target\n"
            "  parameters:\n"
            "    env:\n"
            "      type: projected\n"
            '      value: ".Path[-3]"\n'
            "      description: Env\n"
            "key: source\n"
        )
        target_yaml = (
            "_ocmo:\n"
            "  parameters:\n"
            "    env:\n"
            "      type: projected\n"
            "      value: .Path[-3]\n"
            "      description: Env\n"
            "key: target\n"
        )
        outcome = self._run(source_yaml, target_yaml, mode="whole")
        merged = outcome["merged_yaml"]
        # The double-quoted form from the source YAML must be preserved
        self.assertIn('value: ".Path[-3]"', merged, merged)

    # ------------------------------------------------------------------ ordering

    def test_whole_mode_ocmo_key_order_matches_source(self):
        """mode:whole must place _ocmo at the same position as in the source."""
        source_yaml = (
            "_ocmo:\n"
            "  propagation:\n"
            "    enabled: true\n"
            "    trigger: manual\n"
            "    mode: whole\n"
            "    targets:\n"
            "      - t/target\n"
            "environment: dev\n"
            "app:\n"
            "  name: svc\n"
        )
        target_yaml = (
            "environment: prod\n"
            "app:\n"
            "  name: svc\n"
            "_ocmo:\n"
            "  parameters:\n"
            "    env:\n"
            "      type: projected\n"
            "      value: .Path[1]\n"
            "      description: Env\n"
        )
        outcome = self._run(source_yaml, target_yaml, mode="whole")
        merged = outcome["merged_yaml"]
        keys = [line.split(":")[0] for line in merged.splitlines() if line and not line.startswith(" ")]
        ocmo_idx = keys.index("_ocmo")
        env_idx = keys.index("environment")
        self.assertLess(ocmo_idx, env_idx, f"_ocmo should come before environment; got keys={keys}")

    def test_whole_mode_nested_key_order_matches_source(self):
        """mode:whole reorders nested dict keys (e.g. _ocmo.parameters.env) to match source."""
        source_yaml = (
            "_ocmo:\n"
            "  propagation:\n"
            "    enabled: true\n"
            "    trigger: manual\n"
            "    mode: whole\n"
            "    targets:\n"
            "      - t/target\n"
            "  parameters:\n"
            "    env:\n"
            "      type: projected\n"
            "      value: .Path[-3]\n"
            "      description: Env desc\n"
            "      transformers:\n"
            "        - lower\n"
            "key: source\n"
        )
        target_yaml = (
            "_ocmo:\n"
            "  parameters:\n"
            "    env:\n"
            "      description: Env desc\n"
            "      transformers: []\n"
            "      type: projected\n"
            "      value: .Path[-3]\n"
            "key: target\n"
        )
        outcome = self._run(source_yaml, target_yaml, mode="whole")
        merged = outcome["merged_yaml"]
        # Extract lines within the env parameter block
        env_lines = []
        inside = False
        for line in merged.splitlines():
            if "env:" in line:
                inside = True
                continue
            if inside:
                if line.startswith("      ") and ":" in line:
                    env_lines.append(line.strip().split(":")[0])
                elif line and not line.startswith("      "):
                    break
        # Source has: type, value, description, transformers
        source_order = ["type", "value", "description", "transformers"]
        self.assertEqual(env_lines, source_order, f"nested key order mismatch; got {env_lines}")

    # ------------------------------------------------------------------ target propagation preserved

    def test_whole_mode_target_propagation_block_preserved(self):
        """Target's own _ocmo.propagation must survive mode:whole merge."""
        source_yaml = (
            "_ocmo:\n"
            "  propagation:\n"
            "    enabled: true\n"
            "    trigger: manual\n"
            "    mode: whole\n"
            "    targets:\n"
            "      - t/target\n"
            "key: source-value\n"
        )
        target_yaml = (
            "_ocmo:\n"
            "  propagation:\n"
            "    enabled: true\n"
            "    trigger: tag\n"
            "    tag: stable\n"
            "    mode: data\n"
            "    targets:\n"
            "      - t/downstream\n"
            "key: target-value\n"
        )
        outcome = self._run(source_yaml, target_yaml, mode="whole")
        merged = outcome["merged_yaml"]
        # Target's propagation block must be intact
        self.assertIn("trigger: tag", merged, merged)
        self.assertIn("t/downstream", merged, merged)
        # Source data must have propagated
        self.assertIn("key: source-value", merged, merged)
