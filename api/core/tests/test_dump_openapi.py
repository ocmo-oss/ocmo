"""Tests for offline OpenAPI export."""

import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import SimpleTestCase


class DumpOpenAPICommandTests(SimpleTestCase):
    def test_dump_openapi_writes_schema_to_stdout(self):
        out = StringIO()
        call_command("dump_openapi", stdout=out)
        schema = json.loads(out.getvalue())
        self.assertEqual(schema["openapi"], "3.1.0")
        self.assertIn("paths", schema)
        self.assertTrue(schema["paths"])

    def test_dump_openapi_writes_schema_to_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "openapi.json"
            call_command("dump_openapi", output=str(output))
            schema = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn("/api/health", schema["paths"])

    def test_openapi_hides_db_primary_keys_for_path_addressed_resources(self):
        """Namespaces and tree items are referenced by path/name only."""
        out = StringIO()
        call_command("dump_openapi", stdout=out)
        components = json.loads(out.getvalue())["components"]["schemas"]
        for name in (
            "NamespaceSchema",
            "ConfigSchema",
            "TemplateSchema",
            "SecretSchema",
            "ResolverSchema",
            "FolderSchema",
            "LockSchema",
        ):
            props = components[name]["properties"]
            self.assertNotIn("id", props, msg=name)
        resolver_whoami = components["ResolverWhoAmIDetails"]["properties"]
        self.assertNotIn("namespace_id", resolver_whoami)
        self.assertIn("namespace", resolver_whoami)
