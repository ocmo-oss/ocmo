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
