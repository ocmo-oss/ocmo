import base64

from django.test import TestCase

from core.managers.cast import CastManager


class YamlCastTests(TestCase):
    def test_long_scalar_stays_on_same_line_by_default(self):
        value = base64.b64encode(b"x" * 200).decode()
        out = CastManager("yaml", {}).cast({"aaa": value})
        self.assertRegex(out, r"^aaa: \S+")
        self.assertNotRegex(out, r"^aaa:\n")

    def test_width_option_can_enable_wrapping(self):
        value = base64.b64encode(b"x" * 200).decode()
        out = CastManager("yaml", {"width": 80}).cast({"aaa": value})
        self.assertIn("aaa:", out)
        self.assertRegex(out, r"\n  eHh4")

    def test_multiline_string_uses_literal_block_style(self):
        pem = "----SECRET----\nAJsndLASndlank\nKJANdnkandiOAI\n---END SECRET--"
        out = CastManager("yaml", {}).cast({"env": [{"name": "TLS_CERT", "value": pem}]})
        self.assertIn("value: |", out)
        self.assertIn("----SECRET----", out)
        self.assertNotIn("\\n", out)
