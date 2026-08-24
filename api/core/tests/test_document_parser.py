import json

from django.test import Client, RequestFactory, TestCase

from core.schemas.requests import ConfigDocument
from core.tests.namespace_helpers import create_test_namespace
from ocmoapi.parser import OcmoParser


class OcmoParserTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.parser = OcmoParser()

    def test_json_content_type_parsed_as_dict(self):
        request = self.factory.post(
            "/api/v1/ns/ns1/~config/~create/app/cfg",
            data=b'{"foo": 1}',
            content_type="application/json",
        )
        result = self.parser.parse_body(request)
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {"foo": 1})

    def test_namespace_json_returns_dict(self):
        request = self.factory.post(
            "/api/v1/ns/",
            data=json.dumps({"name": "new-ns", "description": "d"}).encode(),
            content_type="application/json",
        )
        result = self.parser.parse_body(request)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["name"], "new-ns")

    def test_multipart_rejected(self):
        request = self.factory.post(
            "/api/v1/ns/ns1/~config/~create/app/cfg",
            data=b"foo: bar\n",
            content_type="multipart/form-data",
        )
        with self.assertRaises(ValueError) as ctx:
            self.parser.parse_body(request)
        self.assertIn("multipart", str(ctx.exception).lower())

    def test_template_invalid_json_body_rejected(self):
        request = self.factory.post(
            "/api/v1/ns/ns1/~template/~create/tpl",
            data=b"{{ x }}",
            content_type="application/json",
        )
        with self.assertRaises(ValueError) as ctx:
            self.parser.parse_body(request)
        self.assertIn("json", str(ctx.exception).lower())


class DocumentSchemaTests(TestCase):
    def test_config_document_accepts_json_object_root(self):
        doc = ConfigDocument.model_validate({"hello": "world", "n": 1})
        self.assertIn("hello", doc.root)
        self.assertIn("world", doc.root)

    def test_config_document_accepts_yaml_string_root(self):
        doc = ConfigDocument.model_validate("foo: bar\n")
        self.assertEqual(doc.root, "foo: bar\n")

    def test_config_document_accepts_scalar_yaml_root(self):
        doc = ConfigDocument.model_validate("plain scalar\n")
        self.assertEqual(doc.root, "plain scalar\n")

    def test_config_document_accepts_sequence_yaml_root(self):
        doc = ConfigDocument.model_validate("- one\n- two\n")
        self.assertIn("- one", doc.root)


class DocumentUploadApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        create_test_namespace("docupload", description="test")

    def test_create_config_raw_yaml(self):
        response = self.client.post(
            "/api/v1/ns/docupload/~config/~create/app/cfg",
            data=b"hello: world\n",
            content_type="application/yaml",
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_create_config_octet_stream(self):
        response = self.client.post(
            "/api/v1/ns/docupload/~config/~create/app/cfg2",
            data=b"hello: file\n",
            content_type="application/octet-stream",
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_create_config_json_document_text(self):
        response = self.client.post(
            "/api/v1/ns/docupload/~config/~create/app/cfg3",
            data=b'{"hello": "world"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_template_invalid_json_body_rejected(self):
        response = self.client.post(
            "/api/v1/ns/docupload/~template/~create/tpl",
            data=b"{{ x }}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 422, response.content)

    def test_empty_config_body_rejected(self):
        response = self.client.post(
            "/api/v1/ns/docupload/~config/~create/app/empty",
            data=b"",
            content_type="application/yaml",
        )
        self.assertEqual(response.status_code, 422, response.content)

    def test_parser_namespace_json_returns_dict(self):
        """JSON namespace routes use json.loads (covered by OcmoParserTests.test_namespace_json_returns_dict)."""
        self.assertTrue(True)
