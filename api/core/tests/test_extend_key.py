"""Tests for extend config references with ``key`` and ``as``."""

import yaml
from django.core.exceptions import ValidationError
from django.test import TestCase
from pydantic import ValidationError as PydanticValidationError

from core.exceptions import CannotResolveConfig
from core.managers.resolving import ResolvePipelineManager
from core.managers.tree import TreeManager
from core.schemas.requests import ConfigOcmoMetadataSchema, normalize_extend_ref
from core.tests.namespace_helpers import create_test_namespace


class ExtendKeySchemaTests(TestCase):
    def test_string_ref_still_valid(self):
        meta = ConfigOcmoMetadataSchema.model_validate(
            {
                "extend": {"configs": ["bases/a@latest"], "mode": "accumulate"},
            }
        )
        self.assertEqual(meta.extend.configs, ["bases/a@latest"])

    def test_object_ref_valid(self):
        meta = ConfigOcmoMetadataSchema.model_validate(
            {
                "extend": {
                    "configs": [{"path": "shared/all@stable", "key": ".database"}],
                },
            }
        )
        ref = normalize_extend_ref(meta.extend.configs[0])
        self.assertEqual(ref.path, "shared/all@stable")
        self.assertEqual(ref.key, ".database")

    def test_invalid_key_syntax_rejected(self):
        with self.assertRaises(PydanticValidationError):
            ConfigOcmoMetadataSchema.model_validate(
                {
                    "extend": {
                        "configs": [{"path": "shared/all", "key": "database"}],
                    },
                }
            )

    def test_as_with_optional_suffix_rejected(self):
        with self.assertRaises(PydanticValidationError):
            ConfigOcmoMetadataSchema.model_validate(
                {
                    "extend": {
                        "configs": [{"path": "shared/all", "as": ".database?"}],
                    },
                }
            )


class ExtendKeyResolveTests(TestCase):
    def setUp(self):
        self.ns = create_test_namespace("extend-key")

    def _create(self, path: str, body: str) -> None:
        TreeManager(self.ns, path, auth=None).create_item(body, "config")

    def _resolve(self, path: str) -> list[dict]:
        outputs = ResolvePipelineManager(self.ns, path, "latest", auth=None).resolve()
        return [yaml.safe_load(o.data_text) for o in outputs]

    def test_accumulate_key_extracts_at_root(self):
        self._create(
            "shared/all",
            "database:\n  aa: bb\nlogging:\n  level: info\n",
        )
        self._create(
            "app/prod",
            "_ocmo:\n"
            "  extend:\n"
            "    mode: accumulate\n"
            "    configs:\n"
            "      - path: ../shared/all\n"
            "        key: .database\n"
            "cc: dd\n",
        )
        data = self._resolve("app/prod")[0]
        self.assertEqual(data, {"aa": "bb", "cc": "dd"})

    def test_accumulate_key_and_as_wraps_under_as(self):
        self._create(
            "shared/all",
            "database:\n  aa: bb\n",
        )
        self._create(
            "app/prod",
            "_ocmo:\n"
            "  extend:\n"
            "    mode: accumulate\n"
            "    configs:\n"
            "      - path: ../shared/all\n"
            "        key: .database\n"
            "        as: .database\n"
            "database:\n  cc: dd\n",
        )
        data = self._resolve("app/prod")[0]
        self.assertEqual(data, {"database": {"aa": "bb", "cc": "dd"}})

    def test_accumulate_as_only_wraps_whole_document(self):
        self._create(
            "shared/db",
            "host: db.internal\nport: 5432\n",
        )
        self._create(
            "app/prod",
            "_ocmo:\n"
            "  extend:\n"
            "    mode: accumulate\n"
            "    configs:\n"
            "      - path: ../shared/db\n"
            "        as: .persistence.database\n"
            "persistence:\n  database:\n    pool_size: 5\n",
        )
        data = self._resolve("app/prod")[0]
        self.assertEqual(
            data,
            {
                "persistence": {
                    "database": {
                        "host": "db.internal",
                        "port": 5432,
                        "pool_size": 5,
                    }
                }
            },
        )

    def test_optional_key_missing_mapping(self):
        self._create("shared/all", "other: 1\n")
        self._create(
            "app/prod",
            "_ocmo:\n"
            "  extend:\n"
            "    mode: accumulate\n"
            "    configs:\n"
            "      - path: ../shared/all\n"
            "        key: .database?\n"
            "value: ok\n",
        )
        self.assertEqual(self._resolve("app/prod")[0], {"value": "ok"})

    def test_optional_key_missing_index(self):
        self._create("shared/all", "items:\n  - a: 1\n")
        self._create(
            "app/prod",
            "_ocmo:\n"
            "  extend:\n"
            "    mode: accumulate\n"
            "    configs:\n"
            "      - path: ../shared/all\n"
            "        key: .items[2]?\n"
            "value: ok\n",
        )
        data = self._resolve("app/prod")[0]
        self.assertEqual(data["value"], "ok")
        self.assertNotIn("items", data)

    def test_missing_key_without_optional_raises(self):
        self._create("shared/all", "other: 1\n")
        self._create(
            "app/prod",
            "_ocmo:\n  extend:\n    configs:\n      - path: ../shared/all\n        key: .database\nvalue: ok\n",
        )
        with self.assertRaises(CannotResolveConfig):
            self._resolve("app/prod")

    def test_distribute_with_key(self):
        self._create("bases/svc-a", "spec:\n  image: api:1\n  port: 8080\n")
        self._create(
            "app/rollout",
            "_ocmo:\n"
            "  extend:\n"
            "    mode: distribute\n"
            "    by: .overlay\n"
            "    configs:\n"
            "      - path: ../bases/svc-a\n"
            "        key: .spec\n"
            "overlay:\n  replicas: 3\n",
        )
        data = self._resolve("app/rollout")[0]
        self.assertEqual(
            data,
            {"image": "api:1", "port": 8080, "replicas": 3},
        )

    def test_align_with_key(self):
        self._create("bases/a", "defaults:\n  tier: basic\n")
        self._create("bases/b", "defaults:\n  tier: basic\n")
        self._create(
            "app/root",
            "_ocmo:\n"
            "  extend:\n"
            "    mode: align\n"
            "    by: .patches\n"
            "    configs:\n"
            "      - path: ../bases/a\n"
            "        key: .defaults\n"
            "      - path: ../bases/b\n"
            "        key: .defaults\n"
            "patches:\n"
            "  - {tier: premium}\n"
            "  - {tier: standard}\n",
        )
        outputs = self._resolve("app/root")
        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[0], {"tier": "premium"})
        self.assertEqual(outputs[1], {"tier": "standard"})

    def test_param_substitution_on_path_only(self):
        from core.managers.resolve_parameters import ResolveParametersManager
        from core.models import Config

        self._create("bases/prod", "tier: prod\n")
        cfg = Config.objects.get(path="bases/prod", namespace=self.ns)
        root_cfg = Config.objects.create(
            namespace=self.ns,
            path="app/root",
            name="root",
            parent_id=cfg.parent_id,
        )
        metadata = ConfigOcmoMetadataSchema.model_validate(
            {
                "parameters": {
                    "env": {
                        "type": "dynamic",
                        "value": "prod",
                        "description": "Environment name",
                    },
                },
                "extend": {
                    "configs": [
                        {
                            "path": "../bases/{!env}",
                            "key": ".tier",
                        }
                    ],
                },
            }
        )
        params_mgr = ResolveParametersManager(
            self.ns,
            root_cfg,
            base_folder="app",
            version_tag="latest",
            version_number=1,
            dynamic_params={},
            auth=None,
            no_creds=False,
        )
        params_mgr.parameters_effective = {"env": "prod"}
        updated = params_mgr._substitute_metadata(metadata)
        ref = normalize_extend_ref(updated.extend.configs[0])
        self.assertEqual(ref.path, "../bases/prod")
        self.assertEqual(ref.key, ".tier")

    def test_tree_save_validates_object_ref_path(self):
        with self.assertRaises(ValidationError):
            TreeManager(self.ns, "app/missing-ref", auth=None).create_item(
                "_ocmo:\n  extend:\n    configs:\n      - path: ../missing/config\n        key: .database\nvalue: ok\n",
                "config",
            )
