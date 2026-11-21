"""Tests for change-request content helpers."""

from django.test import SimpleTestCase

from core.utils.change_request_content import rewrite_cr_refs_in_body


class RewriteCrRefsTests(SimpleTestCase):
    def test_does_not_match_ten_when_rewriting_one(self):
        body = "_ocmo:\n  extend:\n    configs:\n      - shared/base@~10\n      - shared/base@~1\nkey: peer\n"
        out = rewrite_cr_refs_in_body(
            body,
            node_type="config",
            item_path="app/peer",
            target_resolved_path="shared/base",
            cr_number=1,
            applied_version=2,
        )
        self.assertIn("shared/base@~10", out)
        self.assertIn("- shared/base@2\n", out)
        self.assertNotIn("shared/base@40", out)
        self.assertNotIn("- shared/base@~1\n", out)

    def test_does_not_rewrite_suffix_inside_longer_path(self):
        body = "_ocmo:\n  extend:\n    configs:\n      - other/shared/base@~1\n      - shared/base@~1\nkey: peer\n"
        out = rewrite_cr_refs_in_body(
            body,
            node_type="config",
            item_path="app/peer",
            target_resolved_path="shared/base",
            cr_number=1,
            applied_version=2,
        )
        self.assertIn("- other/shared/base@~1\n", out)
        self.assertIn("- shared/base@2\n", out)

    def test_validation_ref_above_extend_in_file(self):
        body = (
            "_ocmo:\n"
            "  validation:\n"
            "    schema_path: shared/base@~1\n"
            "  extend:\n"
            "    configs:\n"
            "      - shared/base@~1\n"
            "key: x\n"
        )
        out = rewrite_cr_refs_in_body(
            body,
            node_type="config",
            item_path="shared/child/item",
            target_resolved_path="shared/base",
            cr_number=1,
            applied_version=2,
        )
        self.assertEqual(out.count("shared/base@2"), 2)
        self.assertNotIn("@~1", out)
