from django.test import TestCase

from core.exceptions import InvalidCastOption
from core.managers.cast import CastManager


class CastFormatOptionBehaviorTests(TestCase):
    def test_yaml_flow_style_flow(self):
        data = {"items": [1, 2, 3]}
        block = CastManager("yaml", {"flow_style": "block"}).cast(data)
        flow = CastManager("yaml", {"flow_style": "flow"}).cast(data)
        self.assertIn("items:\n", block)
        self.assertIn("items: [", flow.replace("\n", ""))

    def test_json_strict_keys_rejects_integer_keys(self):
        with self.assertRaises(InvalidCastOption):
            CastManager("json", {"strict_keys": True}).cast({1: "a"})

    def test_json_strict_keys_false_coerces_keys(self):
        out = CastManager("json", {"strict_keys": False}).cast({1: "a"})
        self.assertIn('"1"', out)

    def test_env_list_format_joined(self):
        out = CastManager("env", {"list_format": "joined", "list_separator": "|"}).cast({"ports": [8080, 8443]})
        self.assertIn("ports='8080|8443'", out)

    def test_env_comment_header_uses_source_label(self):
        out = CastManager(
            "env",
            {"comment_header": True},
            source_label="app/cfg",
        ).cast({"key": "value"})
        self.assertTrue(out.startswith("# app/cfg\n"))

    def test_env_uppercase_and_lowercase_rejected(self):
        with self.assertRaises(InvalidCastOption):
            CastManager("env", {"uppercase": True, "lowercase": True}).cast({"a": 1})

    def test_hcl_block_style_and_heredoc(self):
        data = {"service": {"command": "line1\nline2"}}
        out = CastManager(
            "hcl",
            {"block_style": "block", "heredoc_strings": True},
        ).cast(data)
        self.assertIn("service {", out)
        self.assertIn("<<-EOT", out)

    def test_hcl_tfvars_flattens_top_level(self):
        out = CastManager("hcl", {"tfvars": True}).cast({"database": {"host": "db"}})
        self.assertIn('database_host = "db"', out)

    def test_raw_encoding_validates_output(self):
        out = CastManager("raw", {"encoding": "utf-8"}).cast("hello")
        self.assertEqual(out, "hello")

        with self.assertRaises(InvalidCastOption):
            CastManager("raw", {"encoding": "ascii"}).cast("héllo")
